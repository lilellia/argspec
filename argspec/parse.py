from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass
import sys
from typing import Any, cast, ClassVar, dataclass_transform, Generic, Protocol, runtime_checkable, Self, TypeVar

from typewire import as_type, is_iterable

from .metadata import _true, Flag, MISSING, Option
from .schema import Schema

C = TypeVar("C")


class ArgumentError(Exception):
    pass


@runtime_checkable
class _ArgSpecMixin(Protocol):
    __argspec_schema__: ClassVar[Schema]

    @classmethod
    def help(cls) -> str: ...

    @classmethod
    def from_argv(cls, argv: Sequence[str] | None = None) -> Self: ...


class ArgSpecClass(Generic[C], _ArgSpecMixin):
    pass


@dataclass_transform()
def argspec(wrapped_cls: type[C]) -> type[ArgSpecClass[C]]:
    wrapped_class = cast(type[ArgSpecClass[C]], dataclass(wrapped_cls))
    wrapped_class.__argspec_schema__ = Schema.for_class(wrapped_cls)

    def help(cls: type[ArgSpecClass[C]]) -> str:
        return cls.__argspec_schema__.help()

    def _from_argv(cls: type[ArgSpecClass[C]], argv: Sequence[str] | None = None) -> ArgSpecClass[C]:
        """Parse the given argv (or sys.argv[1:]) into an instance of the class."""
        if argv is None:
            argv = sys.argv[1:]

        argv = deque(argv)

        schema = cls.__argspec_schema__

        # handle options and flags
        parsed_args: dict[str, Any] = {}
        positional_args: deque[str] = deque()

        while argv:
            token = argv.popleft()
            if token in schema.aliases:
                name = schema.aliases[token]
                type_, meta = schema.args[name]

                if isinstance(meta, Option):
                    try:
                        value = argv.popleft()
                    except IndexError:
                        raise ArgumentError(f"Missing value for option --{name}")

                    try:
                        parsed_args[name] = as_type(value, type_)
                    except ValueError as err:
                        raise ArgumentError(f"Invalid value for option --{name}: {value} ({err})")

                elif isinstance(meta, Flag):
                    parsed_args[name] = not meta.default
                else:
                    raise ArgumentError(f"Unknown argument: {token}")

            elif token in schema.help_keys:
                sys.stderr.write(cls.help() + "\n")
                sys.exit(0)
            else:
                positional_args.append(token)

        # handle positional arguments
        positional_arg_names = list(schema.positional_args.keys())
        for i, (name, (type_, meta)) in enumerate(schema.positional_args.items()):
            if not positional_args:
                if meta.default is not MISSING:
                    parsed_args[name] = meta.default
                elif is_iterable(type_):
                    parsed_args[name] = []
                else:
                    raise ArgumentError(f"Missing positional argument: {name}")
            elif is_iterable(type_):
                parsed_args[name] = []
                arity = schema.nargs_for(name)
                if arity is None:
                    # consume as much as possible
                    further_required = sum(cast(int, schema.nargs_for(name)) for name in positional_arg_names[i + 1 :])
                    arity = len(positional_args) - further_required

                for _ in range(arity):
                    value = positional_args.popleft()
                    parsed_args[name].append(value)

                try:
                    parsed_args[name] = as_type(parsed_args[name], type_)
                except ValueError as err:
                    raise ArgumentError(f"Invalid value for positional argument {name}: {parsed_args[name]} ({err})")
            else:
                value = positional_args.popleft()
                try:
                    parsed_args[name] = as_type(value, type_)
                except ValueError as err:
                    raise ArgumentError(f"Invalid value for positional argument {name}: {value} ({err})")

        # check for remaining positional arguments
        if positional_args:
            raise ArgumentError(f"Extra positional arguments: {', '.join(positional_args)}")

        # go through the arguments and check for unpassed options and apply defaults
        for name, (type_, meta) in schema.args.items():
            value = parsed_args.get(name, meta)

            if isinstance(value, (Option, Flag)):
                if value.default is MISSING:
                    raise ArgumentError(f"Missing value for: --{name}")

                parsed_args[name] = as_type(value.default, type_)

        # run validators
        for name, (type_, meta) in schema.args.items():
            value = parsed_args[name]
            validator = getattr(meta, "validator", _true)

            if not validator(value):
                raise ArgumentError(f"Invalid value for {name}: {value}")

        return cls(**parsed_args)

    def from_argv(cls: type[ArgSpecClass[C]], argv: Sequence[str] | None = None) -> ArgSpecClass[C]:
        """Parse the given argv (or sys.argv[1:]) into an instance of the class."""
        try:
            return _from_argv(cls, argv)
        except ArgumentError as err:
            sys.stderr.write(f"ArgumentError: {err}\n")
            sys.stderr.write(getattr(cls, "help")() + "\n")
            sys.exit(1)

    setattr(wrapped_class, "from_argv", from_argv)
    setattr(wrapped_class, "help", help)

    return wrapped_class
