from pathlib import Path
from typing import Literal

import pytest

from argspec import ArgSpec, ArgumentError, ArgumentSpecError, flag, option, positional


def test_basic_usage() -> None:
    class Config(ArgSpec):
        path: Path = positional()
        port: int = option(8080)
        verbose: bool = flag()

    argv = ["/path/to/file", "--port", "8081", "--verbose"]
    config = Config.from_argv(argv)

    assert config.path == Path("/path/to/file")
    assert config.port == 8081
    assert config.verbose


def test_basic_usage_with_defaults() -> None:
    class Config(ArgSpec):
        path: Path = positional(Path("/path/to/file"))
        port: int = option(8080)
        verbose: bool = flag()

    argv: list[str] = []
    config = Config.from_argv(argv)

    assert config.path == Path("/path/to/file")
    assert config.port == 8080
    assert not config.verbose


def test_short_aliases() -> None:
    class Config(ArgSpec):
        path: Path = positional()
        port: int = option(8080, short=True)
        verbose: bool = flag(short=True)

    argv = ["/path/to/file", "-p", "8081", "-v"]
    config = Config.from_argv(argv)

    assert config.path == Path("/path/to/file")
    assert config.port == 8081
    assert config.verbose


def test_custom_aliases() -> None:
    class Config(ArgSpec):
        path: Path = positional()
        port: int = option(8080, aliases=("-P",))
        verbose: bool = flag(aliases=("-V",))

    argv = ["/path/to/file", "-P", "8081", "-V"]
    config = Config.from_argv(argv)

    assert config.path == Path("/path/to/file")
    assert config.port == 8081
    assert config.verbose


def test_duplicate_option_raises_error() -> None:
    with pytest.raises(ArgumentSpecError):

        class Config(ArgSpec):
            verbose: bool = flag()
            verbose2: bool = flag(aliases=("--verbose",))


def test_duplicate_alias_raises_error() -> None:
    with pytest.raises(ArgumentSpecError):

        class Config(ArgSpec):
            verbose: bool = flag(aliases=("--verbose", "--verbose"))


def test_overriding_help_does_not_raise_error() -> None:
    class Config(ArgSpec):
        help: int = option(short=True)

    argv = ["--help", "3"]
    config = Config.from_argv(argv)

    assert config.help == 3


def test_overriding_dash_h_alias_does_not_raise_error() -> None:
    class Config(ArgSpec):
        host: str = option(short=True)

    argv = ["-h", "localhost"]
    config = Config.from_argv(argv)

    assert config.host == "localhost"


def test_variadic_positional() -> None:
    class Config(ArgSpec):
        path: Path = positional()
        ports: list[int] = option([8080], short=True)
        verbose: bool = flag()

    argv = ["/path/to/file", "-p", "8081", "--verbose"]
    config = Config.from_argv(argv)

    assert config.path == Path("/path/to/file")
    assert config.ports == [8081]
    assert config.verbose


def test_multiple_positionals() -> None:
    class Config(ArgSpec):
        path: Path = positional()
        port: int = positional(8080)
        verbose: bool = flag()

    argv = ["/path/to/file", "8081", "--verbose"]
    config = Config.from_argv(argv)

    assert config.path == Path("/path/to/file")
    assert config.port == 8081
    assert config.verbose


def test_variadic_positional_followed_by_another_positional() -> None:
    class Config(ArgSpec):
        paths: list[Path] = positional()
        port: int = positional(8080)

    argv = ["/path/to/file1", "/path/to/file2", "path/to/file3", "8081"]
    config = Config.from_argv(argv)

    assert config.paths == [Path("/path/to/file1"), Path("/path/to/file2"), Path("path/to/file3")]
    assert config.port == 8081


def test_multiple_variadic_positionals_raises_error() -> None:
    with pytest.raises(ArgumentSpecError):

        class Config(ArgSpec):
            paths: list[Path] = positional()
            ports: list[int] = positional()


def test_variadic_positional_with_default() -> None:
    class Config(ArgSpec):
        ports: list[int] = positional([8080])

    argv: list[str] = []
    config = Config.from_argv(argv)

    assert config.ports == [8080]


def test_variadic_positional_with_missing_value_does_not_raise_error() -> None:
    class Config(ArgSpec):
        ports: list[int] = positional()

    argv: list[str] = []
    config = Config.from_argv(argv)

    assert config.ports == []


def test_variadic_positional_with_missing_value_exits_with_validator() -> None:
    class Config(ArgSpec):
        ports: list[int] = positional(validator=lambda ports: len(ports) > 0)

    argv: list[str] = []
    with pytest.raises(ArgumentError):
        Config._from_argv(argv)


def test_fixed_size_tuple_positional() -> None:
    class Config(ArgSpec):
        paths: tuple[Path, Path] = positional()
        port: int = positional(8080)

    argv = ["/path/to/file1", "/path/to/file2", "8081"]
    config = Config.from_argv(argv)

    assert config.paths == (Path("/path/to/file1"), Path("/path/to/file2"))
    assert config.port == 8081


def test_fixed_size_tuple_insufficient_args() -> None:
    class Config(ArgSpec):
        paths: tuple[Path, Path] = positional()

    argv = ["/path/to/file1"]
    with pytest.raises(ArgumentError):
        Config._from_argv(argv)


def test_variadic_option() -> None:
    class Config(ArgSpec):
        tags: list[str] = option()
        verbose: bool = flag()

    argv = ["--tags", "tag1", "tag2", "tag3", "--verbose"]
    config = Config.from_argv(argv)

    assert config.tags == ["tag1", "tag2", "tag3"]
    assert config.verbose


def test_variadic_option_does_not_leave_space_for_positional() -> None:
    class Config(ArgSpec):
        tags: list[str] = option()
        path: Path = positional()

    argv = ["--tags", "tag1", "tag2", "tag3", "/path/to/file"]

    with pytest.raises(ArgumentError):
        Config._from_argv(argv)


def test_variadic_option_obeys_dash_dash_separator() -> None:
    class Config(ArgSpec):
        tags: list[str] = option()
        path: Path = positional()

    argv = ["--tags", "tag1", "tag2", "tag3", "--", "/path/to/file"]
    config = Config.from_argv(argv)

    assert config.tags == ["tag1", "tag2", "tag3"]
    assert config.path == Path("/path/to/file")


def test_empty_variadic_positional_in_centre() -> None:
    class Config(ArgSpec):
        head: str = positional()
        middle: list[str] = positional()
        tail: str = positional()

    argv = ["head", "tail"]
    config = Config.from_argv(argv)

    assert config.head == "head"
    assert config.middle == []
    assert config.tail == "tail"


def test_empty_optional_variadic_positional_in_centre() -> None:
    class Config(ArgSpec):
        head: str = positional()
        middle: list[str] = positional(["middle", "lines"])
        tail: str = positional()

    argv = ["head", "tail"]
    config = Config.from_argv(argv)

    assert config.head == "head"
    assert config.middle == ["middle", "lines"]
    assert config.tail == "tail"


def test_optional_variadic_positional_in_centre() -> None:
    class Config(ArgSpec):
        head: str = positional()
        middle: list[str] = positional(["middle", "lines"])
        tail: str = positional()

    argv = ["head", "centre", "tail"]
    config = Config.from_argv(argv)

    assert config.head == "head"
    assert config.middle == ["centre"]
    assert config.tail == "tail"


def test_literal_type_hint_as_choices_passes() -> None:
    class Config(ArgSpec):
        mode: Literal["auto", "manual"] = option("auto")

    argv = ["--mode", "manual"]
    config = Config.from_argv(argv)

    assert config.mode == "manual"


def test_literal_type_hint_as_choices_fails() -> None:
    class Config(ArgSpec):
        mode: Literal["auto", "manual"] = option("auto")

    argv = ["--mode", "invalid"]

    with pytest.raises(ArgumentError):
        Config._from_argv(argv)


def test_kebab_case_naming() -> None:
    class Config(ArgSpec):
        some_variable: int = option()

    argv = ["--some-variable", "3"]
    config = Config.from_argv(argv)

    assert config.some_variable == 3


def test_snake_case_naming() -> None:
    class Config(ArgSpec):
        some_variable: int = option()

    argv = ["--some_variable", "3"]
    config = Config.from_argv(argv)

    assert config.some_variable == 3


def test_automatic_flag_negator() -> None:
    class Config(ArgSpec):
        verbose: bool = flag(True)

    argv = ["--no-verbose"]
    config = Config.from_argv(argv)

    assert not config.verbose


def test_manual_flag_negator() -> None:
    class Config(ArgSpec):
        verbose: bool = flag(True, negators=("--quiet",))

    argv = ["--quiet"]
    config = Config.from_argv(argv)

    assert not config.verbose


def test_manual_flag_negator_that_matches_automatic_one_does_not_raise_error() -> None:
    class Config(ArgSpec):
        verbose: bool = flag(True, negators=("--no-verbose",))

    argv = ["--no-verbose"]
    config = Config.from_argv(argv)

    assert not config.verbose


def test_help_output_includes_flag_negators() -> None:
    class Config(ArgSpec):
        verbose: bool = flag(True, negators=("--quiet",))

    help_text = Config.__argspec_schema__.help()
    assert "--quiet" in help_text


def test_repeated_options_last_wins() -> None:
    class Config(ArgSpec):
        port: int = option()

    argv = ["--port", "8080", "--port", "8081"]
    config = Config.from_argv(argv)

    assert config.port == 8081


def test_combined_short_flags_fails() -> None:
    class Config(ArgSpec):
        a: bool = flag()
        b: bool = flag()

    argv = ["-ab"]

    with pytest.raises(ArgumentError):
        Config._from_argv(argv)
