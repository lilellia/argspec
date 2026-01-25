from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass
from io import StringIO
import itertools
from pathlib import Path
import sys
from typing import Any, cast, get_args, get_origin, NamedTuple, TypeVar

from typewire import as_type, is_iterable, TypeHint
from typing_extensions import get_annotations

if sys.version_info >= (3, 11):
    from typing import Self
else:
    from typing_extensions import Self

from .errors import ArgumentError, ArgumentSpecError
from .metadata import _true, Flag, MISSING, Option, Positional
from .readenv import readenv


class ArgvConsumeResult(NamedTuple):
    parsed_args: dict[str, Any]
    positional_args: deque[str]


C = TypeVar("C")


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


def kebabify(text: str, *, lower: bool = False) -> str:
    kebab = text.replace("_", "-")
    return kebab.lower() if lower else kebab


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
    flag_negators: dict[str, str]

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

    @property
    def named_tokens(self) -> set[str]:
        return set(self.aliases.keys()) | set(self.flag_negators.keys())

    @staticmethod
    def make_short(name: str) -> str:
        return f"-{name.lstrip('-')[0]}"

    def is_flag(self, token: str) -> bool:
        token = self.aliases.get(token, token)

        if token.lstrip("-") in (*self.flag_args.keys(), *self.flag_negators.keys()):
            return True

        if any(meta.short and token == self.make_short(name) for name, (_, meta) in self.flag_args.items()):
            return True

        return False

    def nargs_for(self, name: str) -> int | None:
        type_, _ = self.args[name]
        return get_container_length(type_)

    @classmethod
    def for_class(cls, wrapped_cls: type[C]) -> Self:
        args: dict[str, tuple[TypeHint, Positional[Any] | Option[Any] | Flag]] = {}
        aliases: dict[str, str] = {}
        flag_negators: dict[str, str] = {}
        for name, annot in get_annotations(wrapped_cls, eval_str=True).items():
            # get the value of the attribute; will be MISSING if
            # 1) the value was never set, e.g., `x: int`
            # 2) the value was set to dataclasses.field, e.g., `y: list[int] = field(default_factory=list)`,
            #    since dataclasses will generally remove these from the class dict
            value = getattr(wrapped_cls, name, MISSING)

            if not isinstance(value, (Positional, Option, Flag)):
                # value is not an argspec object, so we'll just ignore it, letting the dataclass handle it
                continue

            args[name] = (annot, value)
            kebab_name = kebabify(name, lower=True)

            if isinstance(value, (Option, Flag)):
                if f"--{kebab_name}" in aliases:
                    raise ArgumentSpecError(f"Duplicate option: --{name}")

                aliases[f"--{kebab_name}"] = name

                if name != kebab_name:
                    if f"--{name}" in aliases:
                        raise ArgumentSpecError(f"Duplicate option: --{name}")

                    aliases[f"--{name}"] = name

                for alias in value.aliases or []:
                    if alias in aliases:
                        raise ArgumentSpecError(f"Duplicate option alias: {alias}")
                    aliases[alias] = name

                if value.short:
                    if (short := cls.make_short(name)) in aliases:
                        raise ArgumentSpecError(f"Duplicate option alias: {short}")
                    aliases[short] = name

            # flag negators
            if isinstance(value, Flag):
                for negator in value.negators or []:
                    if negator in (*aliases.keys(), *flag_negators.keys()):
                        raise ArgumentSpecError(f"Duplicate flag negator: {negator}")

                    flag_negators[negator] = name

                # provide a default negator for flags that default to True when no other negator is provided
                if value.default is True and not value.negators and (negator := f"--no-{kebab_name}") not in aliases:
                    flag_negators[negator] = name

        return cls(args=args, aliases=aliases, flag_negators=flag_negators)

    def get_all_names_for(self, name: str, meta: Option[Any] | Flag) -> list[str]:
        names = [kebabify(name if name.startswith("-") else f"--{name}", lower=True)]

        if meta.aliases:
            names = [*meta.aliases, *names]

        if meta.short:
            names = [f"-{name[0]}", *names]

        return names

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

        # help/usage message
        if self.help_keys:
            names = ", ".join(self.help_keys)
            buffer.write(f"    {names}\n")
            buffer.write("    Print this message and exit\n\n")

        # flags

        meta: Flag | Option[Any] | Positional[Any]

        for name, (type_, meta) in self.flag_args.items():
            names = ", ".join(self.get_all_names_for(name, meta))

            type_name = type_.__name__ if hasattr(type_, "__name__") else str(type_)
            buffer.write(f"    true: {names}\n")

            if negators := {k for k, v in self.flag_negators.items() if v == name}:
                buffer.write(f"    false: {', '.join(negators)}\n")

            buffer.write(f"    {meta.help or ''}")
            buffer.write(f" (default: {meta.default})")

            buffer.write("\n\n")

        # values
        for name, (type_, meta) in self.option_args.items():
            names = ", ".join(self.get_all_names_for(name, meta))

            type_name = type_.__name__ if hasattr(type_, "__name__") else str(type_)
            buffer.write(f"    {names} {name.upper()} <{type_name}>\n")
            buffer.write(f"    {meta.help or ''}")

            if (default := meta.default) is not MISSING:
                buffer.write(f" (default: {default})")
            elif (factory := meta.default_factory) is not None:
                if isinstance(factory, readenv):
                    # get the current value of the variable
                    current = factory()
                    if current is MISSING:
                        current = "<unset>"
                    else:
                        current = repr(current)

                    # print a useful message for the user
                    if factory.default is MISSING:
                        buffer.write(f" (default: ${factory.key} (currently: {current}))")
                    else:
                        buffer.write(f" (default: ${factory.key} or {factory.default!r} (currently: {current}))")
                else:
                    buffer.write(f" (default: {factory()})")

            buffer.write("\n\n")

        # positional arguments
        buffer.write("\nArguments:\n")
        for name, (type_, meta) in self.positional_args.items():
            type_name = type_.__name__ if hasattr(type_, "__name__") else str(type_)
            buffer.write(f"    {kebabify(name.upper())} <{type_name}>\n")
            buffer.write(f"    {meta.help or ''}")

            if meta.default is not MISSING:
                buffer.write(f" (default: {meta.default})")

            buffer.write("\n\n")

        return buffer.getvalue()

    def pop_until_next_token_or_limit(self, pool: deque[str], name: str, arity: int | None) -> list[str]:
        tokens: list[str] = []

        for taken in itertools.count():
            if arity is not None and taken >= arity:
                # we've hit the arity limit
                break

            if not pool:
                # we've run out of tokens to take
                if arity is None:
                    # this is fine, because we were just picking until we ran out
                    break

                raise ArgumentError(f"Missing value for option --{kebabify(name)}")

            val = pool.popleft()
            if val in self.named_tokens:
                # this is another token, so put it back
                pool.appendleft(val)
                break

            if val == "--":
                # we've hit the end of the available tokens
                break

            tokens.append(val)

        return tokens

    def consume_argv(self, argv: deque[str]) -> ArgvConsumeResult:
        parsed_args: dict[str, Any] = {}
        positional_args: deque[str] = deque()

        while argv:
            token = argv.popleft()

            if token == "--":
                positional_args.extend(argv)
                break

            if token.startswith("-") and "=" in token:
                # allow `--key=value` to be interpreted as `--key value`
                # by stripping out the value and just adding it back into the pool
                token, val = token.split("=", maxsplit=1)

                if self.is_flag(token):
                    raise ArgumentError(f"Flag {token} does not take a value (`{token}={val}`)")

                argv.appendleft(val)

            if token not in self.named_tokens:
                positional_args.append(token)
                continue

            if token in self.flag_negators:
                name = self.flag_negators[token]
                parsed_args[name] = False
                continue

            name = self.aliases[token]
            type_, meta = self.args[name]

            if isinstance(meta, Option):
                try:
                    value = (
                        self.pop_until_next_token_or_limit(argv, name, arity=self.nargs_for(name))
                        if is_iterable(type_)
                        else argv.popleft()
                    )
                except IndexError:
                    raise ArgumentError(f"Missing value for option --{kebabify(name)}")
                except ArgumentError:
                    raise

                try:
                    parsed_args[name] = as_type(value, type_)
                except ValueError as err:
                    raise ArgumentError(f"Invalid value for option --{kebabify(name)}: {value} ({err})")

            elif isinstance(meta, Flag):
                parsed_args[name] = True

            else:
                raise ArgumentError(f"Unknown argument: {token}")

        return ArgvConsumeResult(parsed_args, positional_args)

    def required_positionals_after(self, name: str) -> int:
        names = list(self.positional_args.keys())
        index = names.index(name)

        nargs = [cast(int, self.nargs_for(arg)) for arg in names[index + 1 :]]
        return sum(max(1, n) for n in nargs)

    def assign_positional_arg(self, name: str, positional_args: deque[str]) -> Any:
        type_, meta = self.args[name]
        assert isinstance(meta, Positional)

        if not positional_args:
            if meta.default is not MISSING:
                return as_type(meta.default, type_)

            if meta.default_factory is not None:
                if (default := meta.default_factory()) is MISSING:
                    raise ArgumentError(f"Missing positional argument: {name}")

                return as_type(default, type_)

            if is_iterable(type_):
                return as_type([], type_)

            raise ArgumentError(f"Missing positional argument: {name}")

        if not is_iterable(type_):
            value = positional_args.popleft()
            try:
                return as_type(value, type_)
            except ValueError as err:
                raise ArgumentError(f"Invalid value for positional argument {name}: {value} ({err})")

        collected = []

        if (arity := self.nargs_for(name)) is None:
            # consume as much as possible
            arity = len(positional_args) - self.required_positionals_after(name)

        for _ in range(arity):
            try:
                value = positional_args.popleft()
            except IndexError:
                raise ArgumentError(f"Missing value for positional argument {name}")
            collected.append(value)

        if not collected and meta.default is not MISSING:
            return as_type(meta.default, type_)

        try:
            return as_type(collected, type_)
        except ValueError as err:
            raise ArgumentError(f"Invalid value for positional argument {name}: {collected} ({err})")

    def assign_positional_args(self, parsed_args: dict[str, Any], positional_args: deque[str]) -> None:
        """Update the parsed_args dict by assigning the positional arguments according to the schema."""
        for name in self.positional_args.keys():
            parsed_args[name] = self.assign_positional_arg(name, positional_args)

    def raise_if_extra_positional_args(self, positional_args: deque[str]) -> None:
        if positional_args:
            raise ArgumentError(f"Too many positional arguments: {', '.join(positional_args)}")

    def apply_defaults(self, parsed_args: dict[str, Any]) -> None:
        for name, (type_, meta) in self.args.items():
            value = parsed_args.get(name, meta)

            if isinstance(value, Flag):
                parsed_args[name] = as_type(value.default, type_)

            if isinstance(value, Option):
                if value.default is not MISSING:
                    parsed_args[name] = as_type(value.default, type_)
                    continue

                if value.default_factory is None or (default := value.default_factory()) is MISSING:
                    raise ArgumentError(f"Missing value for: --{kebabify(name)}")

                parsed_args[name] = as_type(default, type_)

    def run_validators(self, parsed_args: dict[str, Any]) -> None:
        for name, (type_, meta) in self.args.items():
            value = parsed_args[name]
            validator = getattr(meta, "validator", _true)

            if not validator(value):
                raise ArgumentError(f"Invalid value for {kebabify(name)}: {value}")

    def parse_args(self, argv: Sequence[str] | None = None) -> dict[str, Any]:
        """Parse the given argv (or sys.argv[1:]) into a dict according to the schema."""
        argv = deque(argv if argv is not None else sys.argv[1:])

        # check for help
        if set(argv) & set(self.help_keys):
            sys.stderr.write(self.help() + "\n")
            sys.exit(0)

        try:
            # handle options and flags
            # note that parsed_args and positional_args are mutated throughout this chain
            parsed_args, positional_args = self.consume_argv(argv)

            self.assign_positional_args(parsed_args, positional_args)
            self.raise_if_extra_positional_args(positional_args)
            self.apply_defaults(parsed_args)
            self.run_validators(parsed_args)
        except ArgumentError:
            raise

        return parsed_args
