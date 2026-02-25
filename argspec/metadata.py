from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
import sys
from typing import Any, Generic, overload, TYPE_CHECKING, TypedDict, TypeVar

from .errors import ArgumentSpecError

S = TypeVar("S")
T = TypeVar("T")


def _true(_: T, /) -> bool:
    return True


class MissingType:
    pass


MISSING = MissingType()


def is_mutable(value: Any) -> bool:
    """Determine if the given value is of a mutable type.

    This uses the same test logic as dataclasses.field:

    ```py
    # For real fields, disallow mutable defaults.  Use unhashable as a proxy
    # indicator for mutability.  Read the __hash__ attribute from the class,
    # not the instance.
    if f._field_type is _FIELD and f.default.__class__.__hash__ is None:
        raise ValueError(f'mutable default {type(f.default)} for field '
                         f'{f.name} is not allowed: use default_factory')
    ```
    """
    return value.__class__.__hash__ is None


def assign_default_and_factory(
    default: T | MissingType, default_factory: Callable[[], T] | None = None
) -> tuple[T | MissingType, Callable[[], T] | None]:
    match default, default_factory:
        case MissingType(), None:
            return MISSING, None

        case MissingType(), factory:
            return MISSING, factory

        case value, None:
            if is_mutable(value):
                # dataclasses.field will not allow mutable defaults
                # so we wrap it in a default_factory instead
                return MISSING, lambda: value

            return value, None

        case _:
            raise ArgumentSpecError("Cannot specify both default and default_factory")


@dataclass
class Positional(Generic[S, T]):
    default: S | MissingType
    default_factory: Callable[[], S] | None
    converter: Callable[[str], S] | None
    validator: Callable[[T], bool]
    help: str | None

    def is_required(self) -> bool:
        return self.default is MISSING and self.default_factory is None


@dataclass
class Option(Generic[S, T]):
    default: S | MissingType
    default_factory: Callable[[], S] | None
    converter: Callable[[str], S] | None
    short: bool
    long: bool
    aliases: Sequence[str]
    validator: Callable[[S, T], bool]
    help: str | None

    def is_required(self) -> bool:
        return self.default is MISSING and self.default_factory is None


@dataclass
class Flag:
    default: bool
    short: bool
    long: bool
    aliases: Sequence[str]
    negators: Sequence[str]
    help: str | None


class ArgSpecMetadata(TypedDict):
    argspec: Positional[Any, Any] | Option[Any, Any] | Flag


# The positional, option, flag functions are typed to return Any so that they can be used as the values in the
# dataclass fields. That is,
#    port: int = option(8080, aliases=("-p",), help="The port to listen on")
# should succeed, but type checkers will (correctly) realise that the RHS is not an int. But typing the function
# as -> Any will bypass the typing check.

if TYPE_CHECKING:

    @overload
    def positional(
        default: S = ...,
        *,
        converter: Callable[[str], S] | None = None,
        validator: Callable[[T], bool] = _true,
        help: str | None = None,
    ) -> T: ...

    @overload
    def positional(
        *,
        default_factory: Callable[[], S] | None = None,
        converter: Callable[[str], S] | None = None,
        validator: Callable[[T], bool] = _true,
        help: str | None = None,
    ) -> T: ...

    def positional(
        default: S = ...,
        *,
        default_factory: Callable[[], S] | None = None,
        converter: Callable[[str], S] | None = None,
        validator: Callable[[T], bool] = _true,
        help: str | None = None,
    ) -> T: ...

    @overload
    def option(
        default: S = ...,
        *,
        converter: Callable[[str], S] | None = None,
        short: bool = False,
        long: bool = True,
        aliases: Sequence[str] | None = None,
        validator: Callable[[T], bool] = _true,
        help: str | None = None,
    ) -> T: ...

    @overload
    def option(
        *,
        default_factory: Callable[[], S] | None = None,
        converter: Callable[[str], S] | None = None,
        short: bool = False,
        long: bool = True,
        aliases: Sequence[str] | None = None,
        validator: Callable[[T], bool] = _true,
        help: str | None = None,
    ) -> T: ...

    def option(
        default: S = ...,
        *,
        default_factory: Callable[[], S] | None = None,
        converter: Callable[[str], S] | None = None,
        short: bool = False,
        long: bool = True,
        aliases: Sequence[str] | None = None,
        validator: Callable[[T], bool] = _true,
        help: str | None = None,
    ) -> T: ...

    def flag(
        default: bool = False,
        *,
        short: bool = False,
        long: bool = True,
        aliases: Sequence[str] | None = None,
        negators: Sequence[str] | None = None,
        help: str | None = None,
    ) -> bool: ...

else:

    def positional(
        default: S | MissingType = MISSING,
        *,
        default_factory: Callable[[], S] | None = None,
        converter: Callable[[str], S] | None = None,
        validator: Callable[[T], bool] = _true,
        help: str | None = None,
    ) -> Any:
        # extra keyword arguments to pass directly to the dataclass.field object
        extra: dict[str, Any] = {}
        if sys.version_info >= (3, 14):
            extra["doc"] = help

        obj = Positional(
            default=default,
            default_factory=default_factory,
            converter=converter,
            validator=validator,
            help=help,
        )

        metadata = ArgSpecMetadata(argspec=obj)

        match assign_default_and_factory(default, default_factory):
            case MissingType(), None:
                return field(default=MISSING, metadata=metadata, **extra)

            case MissingType(), factory:
                assert factory is not None
                return field(default_factory=factory, metadata=metadata, **extra)

            case value, None:
                return field(default=value, metadata=metadata, **extra)

            case _:
                raise ArgumentSpecError("Cannot specify both default and default_factory")

    def option(
        default: S | MissingType = MISSING,
        *,
        default_factory: Callable[[], S] | None = None,
        converter: Callable[[str], S] | None = None,
        short: bool = False,
        long: bool = True,
        aliases: Sequence[str] | None = None,
        validator: Callable[[T], bool] = _true,
        help: str | None = None,
    ) -> Any:
        if default is not MISSING and default_factory is not None:
            raise ArgumentSpecError("Cannot specify both default and default_factory")

        if not short and not long and not aliases:
            raise ArgumentSpecError("At least one of short, long, or aliases must be provided")

        # extra keyword arguments to pass directly to the dataclass.field object
        extra: dict[str, Any] = {}
        if sys.version_info >= (3, 14):
            extra["doc"] = help

        obj = Option(
            default=default,
            default_factory=default_factory,
            converter=converter,
            short=short,
            long=long,
            aliases=aliases or [],
            validator=validator,
            help=help,
        )

        metadata = ArgSpecMetadata(argspec=obj)

        match assign_default_and_factory(default, default_factory):
            case MissingType(), None:
                return field(default=MISSING, metadata=metadata, **extra)

            case MissingType(), factory:
                assert factory is not None
                return field(default_factory=factory, metadata=metadata, **extra)

            case value, None:
                return field(default=value, metadata=metadata, **extra)

            case _:
                raise ArgumentSpecError("Cannot specify both default and default_factory")

    def flag(
        default: bool = False,
        *,
        short: bool = False,
        long: bool = True,
        aliases: Sequence[str] | None = None,
        negators: Sequence[str] | None = None,
        help: str | None = None,
    ) -> Any:
        if not short and not long and not aliases:
            raise ArgumentSpecError("At least one of short, long, or aliases must be provided")

        # extra keyword arguments to pass directly to the dataclass.field object
        extra: dict[str, Any] = {}
        if sys.version_info >= (3, 14):
            extra["doc"] = help

        obj = Flag(default=default, short=short, long=long, aliases=aliases or [], negators=negators or [], help=help)

        metadata = ArgSpecMetadata(argspec=obj)

        return field(default=default, metadata=metadata, **extra)
