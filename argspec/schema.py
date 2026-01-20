from dataclasses import dataclass
from io import StringIO
from pathlib import Path
import sys
from typing import Any, cast, get_args, get_origin, Self, TypeVar

from typewire import is_iterable, TypeHint
from typing_extensions import get_annotations

from .metadata import Flag, MISSING, Option, Positional

C = TypeVar("C")


class ArgumentSpecError(Exception):
    pass


def get_container_length(type_hint: TypeHint) -> int | None:
    """Get the length of a container type. Return 0 for noncontainers, None for containers of unknown length.

    >>> get_container_length(int)
    0

    >>> get_container_length(list[int])  # arbitrary length
    None

    >>> get_container_length(tuple[int, str])
    2

    >>> get_container_length(tuple[int, ...])
    None
    """
    if not is_iterable(type_hint):
        return 0

    if type_hint in (str, bytes):
        # specifically handle Iterable[str] and Iterable[bytes] as simply str and bytes
        return 0

    args = get_args(type_hint)
    origin = get_origin(type_hint)

    # if tuple[T, T] fixed length
    if cast(Any, origin) is tuple:
        if not args:
            return None

        return None if Ellipsis in args else len(args)

    # otherwise, it's a variadic container
    return None


def format_help_message_for_positional(name: str, type_: TypeHint, meta: Positional[Any]) -> str:
    match get_container_length(type_):
        case 0:
            value = name.upper()
        case None:
            value = f"{name.upper()} [{name.upper()}...]"
        case n:
            value = " ".join([name.upper() for _ in range(n)])

    return value if meta.is_required() else f"[{value}]"


@dataclass(frozen=True, slots=True)
class Schema:
    args: dict[str, tuple[TypeHint, Positional[Any] | Option[Any] | Flag]]
    aliases: dict[str, str]

    def __post_init__(self) -> None:
        arities = [self.nargs_for(name) for name in self.positional_args.keys()]
        if arities.count(None) > 1:
            raise ArgumentSpecError("Multiple positional arguments with arbitrary length")

    @property
    def positional_args(self) -> dict[str, tuple[TypeHint, Positional[Any]]]:
        return {name: (type_, meta) for name, (type_, meta) in self.args.items() if isinstance(meta, Positional)}

    @property
    def option_args(self) -> dict[str, tuple[TypeHint, Option[Any]]]:
        return {name: (type_, meta) for name, (type_, meta) in self.args.items() if isinstance(meta, Option)}

    @property
    def flag_args(self) -> dict[str, tuple[TypeHint, Flag]]:
        return {name: (type_, meta) for name, (type_, meta) in self.args.items() if isinstance(meta, Flag)}

    @property
    def help_keys(self) -> list[str]:
        return [k for k in ("-h", "--help") if k not in {**self.args, **self.aliases}.keys()]

    def nargs_for(self, name: str) -> int | None:
        type_, _ = self.args[name]
        return get_container_length(type_)

    @classmethod
    def for_class(cls, wrapped_cls: type[C]) -> Self:
        args = {}
        aliases = {}
        for name, annot in get_annotations(wrapped_cls, eval_str=True).items():
            value = getattr(wrapped_cls, name)
            args[name] = (annot, value)

            if isinstance(value, (Option, Flag)):
                if f"--{name}" in aliases:
                    raise ValueError(f"Duplicate option: --{name}")

                aliases[f"--{name}"] = name

                for alias in value.aliases or []:
                    if alias in aliases:
                        raise ValueError(f"Duplicate option alias: {alias}")
                    aliases[alias] = name

        return cls(args=args, aliases=aliases)

    def help(self) -> str:
        """Return a help string for the given argument specification schema."""
        buffer = StringIO()

        buffer.write("Usage:\n")
        positionals = " ".join(
            format_help_message_for_positional(name, type_, meta)
            for name, (type_, meta) in self.positional_args.items()
        )
        prog = Path(sys.argv[0]).name

        buffer.write(f"    {prog} [OPTIONS] {positionals}\n\n")
        buffer.write("Options:\n")

        # flags
        if self.help_keys:
            help_ = {self.help_keys[0]: (bool, Flag(aliases=self.help_keys[1:], help="Print this message and exit"))}
        else:
            help_ = {}

        meta: Flag | Option[Any] | Positional[Any]

        for name, (type_, meta) in {**help_, **self.flag_args}.items():
            display_name = name if name.startswith("-") else f"--{name}"
            names = [*meta.aliases, display_name] if meta.aliases else [display_name]
            name_str = ", ".join(names)

            type_name = type_.__name__ if hasattr(type_, "__name__") else str(type_)
            buffer.write(f"    {name_str}\n")
            buffer.write(f"    {meta.help or ''}")
            buffer.write(f" (default: {meta.default})")

            buffer.write("\n\n")

        # values
        for name, (type_, meta) in self.option_args.items():
            display_name = name if name.startswith("-") else f"--{name}"
            names = [*meta.aliases, display_name] if meta.aliases else [display_name]
            name_str = ", ".join(names)

            type_name = type_.__name__ if hasattr(type_, "__name__") else str(type_)
            buffer.write(f"    {name_str} {name.upper()} <{type_name}>\n")
            buffer.write(f"    {meta.help or ''}")

            if meta.default is not MISSING:
                buffer.write(f" (default: {meta.default})")

            buffer.write("\n\n")

        # positional arguments
        buffer.write("\nArguments:\n")
        for name, (type_, meta) in self.positional_args.items():
            type_name = type_.__name__ if hasattr(type_, "__name__") else str(type_)
            buffer.write(f"    {name.upper()} <{type_name}>\n")
            buffer.write(f"    {meta.help or ''}")

            if meta.default is not MISSING:
                buffer.write(f" (default: {meta.default})")

            buffer.write("\n\n")

        return buffer.getvalue()
