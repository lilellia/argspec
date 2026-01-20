from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass
import sys
from typing import Any, cast, dataclass_transform, Self

from typewire import as_type, is_iterable

from .metadata import _true, Flag, MISSING, Option
from .schema import Schema


class ArgumentError(Exception):
    pass


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
    def help(cls) -> str:
        return cls.__argspec_schema__.help()

    @classmethod
    def _from_argv(cls, argv: Sequence[str] | None = None) -> Self:
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

    @classmethod
    def from_argv(cls, argv: Sequence[str] | None = None) -> Self:
        """Parse the given argv (or sys.argv[1:]) into an instance of the class."""
        try:
            return cls._from_argv(argv)
        except ArgumentError as err:
            sys.stderr.write(f"ArgumentError: {err}\n")
            sys.stderr.write(getattr(cls, "help")() + "\n")
            sys.exit(1)
