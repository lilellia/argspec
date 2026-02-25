from collections.abc import Sequence
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

    def __new__(mcs, name: str, bases: tuple[type, ...], namespace: dict[str, Any], **kwargs: Any) -> type:
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)

        if name == "ArgSpec":
            return cls

        cls = cast(Any, dataclass(cls))
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
