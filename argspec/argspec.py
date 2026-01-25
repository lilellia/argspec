from collections.abc import Sequence
from dataclasses import dataclass
import sys
from typing import Any, cast

if sys.version_info >= (3, 11):
    from typing import dataclass_transform, Self
else:
    from typing_extensions import dataclass_transform, Self


from .errors import ArgumentError
from .parse import Schema


@dataclass_transform()
class ArgSpecMeta(type):
    __argspec_schema__: Schema

    def __new__(mcs, name: str, bases: tuple[type, ...], namespace: dict[str, Any], **kwargs: Any) -> type:
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)

        if name == "ArgSpec":
            return cls

        cls = cast(Any, dataclass(cls))
        cls.__argspec_schema__ = Schema.for_class(cls)

        return cast(type, cls)


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
