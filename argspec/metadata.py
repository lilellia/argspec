from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from .errors import ArgumentSpecError

T = TypeVar("T")


def _true(_: T, /) -> bool:
    return True


class MissingType:
    def __repr__(self) -> str:
        return "MISSING"


MISSING = MissingType()


@dataclass(frozen=True, slots=True)
class Positional(Generic[T]):
    default: T | MissingType = MISSING
    default_factory: Callable[[], T] | None = None
    validator: Callable[[T], bool] = _true
    help: str | None = None

    def is_required(self) -> bool:
        return self.default is MISSING


@dataclass(frozen=True, slots=True)
class Option(Generic[T]):
    default: T | MissingType = MISSING
    default_factory: Callable[[], T] | None = None
    short: bool = False
    aliases: Sequence[str] | None = field(default_factory=list)
    validator: Callable[[T], bool] = _true
    help: str | None = None

    def is_required(self) -> bool:
        return self.default is MISSING


@dataclass(frozen=True, slots=True)
class Flag:
    default: bool = False
    short: bool = False
    aliases: Sequence[str] | None = field(default_factory=list)
    negators: Sequence[str] | None = field(default_factory=list)
    help: str | None = None


# The positional, option, flag functions are typed to return Any, rather than the actual dataclass types (above)
# that they return so that they can be used as the values in the dataclass fields. That is,
#    port: int = option(8080, aliases=("-p",), help="The port to listen on")
# should succeed, but type checkers will (correctly) realise that the RHS is not an int. But typing the function
# as -> Any will bypass the typing check.


def positional(
    default: T | MissingType = MISSING,
    *,
    default_factory: Callable[[], T] | None = None,
    validator: Callable[[T], bool] = _true,
    help: str | None = None,
) -> Any:
    if default is not MISSING and default_factory is not None:
        raise ArgumentSpecError("Cannot specify both default and default_factory")

    return Positional(default=default, default_factory=default_factory, validator=validator, help=help)


def option(
    default: T | MissingType = MISSING,
    *,
    default_factory: Callable[[], T] | None = None,
    short: bool = False,
    aliases: Sequence[str] | None = None,
    validator: Callable[[T], bool] = _true,
    help: str | None = None,
) -> Any:
    if default is not MISSING and default_factory is not None:
        raise ArgumentSpecError("Cannot specify both default and default_factory")

    return Option(
        default=default, default_factory=default_factory, short=short, aliases=aliases, validator=validator, help=help
    )


def flag(
    default: bool = False,
    *,
    short: bool = False,
    aliases: Sequence[str] | None = None,
    negators: Sequence[str] | None = None,
    help: str | None = None,
) -> Any:
    return Flag(default=default, short=short, aliases=aliases, negators=negators, help=help)
