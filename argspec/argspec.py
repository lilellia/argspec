from collections.abc import Sequence
import dataclasses
from dataclasses import dataclass
import sys
from typing import Any, cast, TYPE_CHECKING

if sys.version_info >= (3, 11):
    from typing import dataclass_transform, Self
else:
    from typing_extensions import dataclass_transform, Self


from .errors import ArgumentError
from .parse import Schema


class ArgSpecMeta(type):
    __argspec_schema__: Schema

    def __new__(
        mcs,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        frozen: bool = True,
        **kwargs: Any,
    ) -> type:
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)

        if name == "ArgSpec":
            return cls

        cls = cast(Any, dataclass(cls, frozen=frozen))
        cls.__argspec_schema__ = Schema.for_class(cls)

        return cast(type, cls)

    if not TYPE_CHECKING:

        def __call__(cls, *args: Any, __ARGSPEC_SKIP_VALIDATION__: bool = False, **kwargs: Any) -> Any:
            # inst will be the "normal" instance that's a result of
            # inst = Args.__init__(self, *args, **kwargs)

            inst = super().__call__(*args, **kwargs)

            if __ARGSPEC_SKIP_VALIDATION__:
                return inst

            # we intercept that instance and validate it with the schema
            # which means injecting default values, reapplying validators, etc.
            schema = cls.__argspec_schema__
            return schema.validate(inst)


@dataclass_transform()
class ArgSpec(metaclass=ArgSpecMeta):
    @classmethod
    def __help(cls) -> str:
        return cls.__argspec_schema__.help()

    @classmethod
    def _from_argv(cls, argv: Sequence[str] | None = None) -> Self:
        """Parse the given argv (or sys.argv[1:]) into an instance of the class."""
        kwargs = cls.__argspec_schema__.parse_args(argv)
        return cls(**kwargs)

    @classmethod
    def from_argv(cls, argv: Sequence[str] | None = None) -> Self:
        """Parse the given argv (or sys.argv[1:]) into an instance of the class."""
        try:
            return cls._from_argv(argv)
        except ArgumentError as err:
            sys.stderr.write(f"ArgumentError: {err}\n")
            sys.stderr.write(cls.__help() + "\n")
            sys.exit(1)

    def replace(self, **kwargs: Any) -> Self:
        """Return a new instance with the given changes applied, re-applying type coercion and validators.
           Raises TypeError if any of the keys is unrecognised; ValueError if any of the values are invalid.
           If kwargs contains __ARGSPEC_SKIP_VALIDATION__ = True, validation will be skipped, which is dangerous.

        class Args(ArgSpec):
            x: int = positional()
            y: int = positional(validator=lambda y: y > 0)

        >>> args = Args(x="1", y="2")  # str -> int is coercible
        >>> args
        Args(x=1, y=2)

        >>> args.replace(x="-1")
        Args(x=-1, y=2)

        >>> args.replace(y="str")  # this string can't be coerced to int
        ValueError: Invalid value for y: 'str' (invalid literal for int() with base 10: 'str')

        >>> args.replace(y="-123")
        ArgumentError: Invalid value for y: -123

        # __ARGSPEC_SKIP_VALIDATION__ will skip validation, though obviously, this is dangerous
        >>> args.replace(y="-123", __ARGSPEC_SKIP_VALIDATION__=True)
        Args(x=1, y=-123)

        >>> args.replace(z=1)
        TypeError: Args.__init__() got an unexpected keyword argument 'z'

        """

        if kwargs.pop("__ARGSPEC_SKIP_VALIDATION__", False):
            kw = {**self.__dict__, **kwargs}
            try:
                return type(self)(**kw, __ARGSPEC_SKIP_VALIDATION__=True)  #  type: ignore[call-arg]
            except ArgumentError as err:
                raise ValueError(str(err)) from err

        try:
            return dataclasses.replace(self, **kwargs)  # type: ignore[type-var]
        except ArgumentError as err:
            raise ValueError(str(err)) from err
