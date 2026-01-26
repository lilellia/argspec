from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
import re

import pytest

from argspec import ArgSpec, flag, option, positional


def test_positional_help() -> None:
    class Config(ArgSpec):
        path: str = positional(help="some random help string")

    help_text = Config.__argspec_schema__.help()
    assert "some random help string" in help_text


def test_flag_help() -> None:
    class Config(ArgSpec):
        verbose: bool = flag(help="some random help string")

    help_text = Config.__argspec_schema__.help()
    assert "some random help string" in help_text


def test_option_help_shows_option_name() -> None:
    class Config(ArgSpec):
        path: str = option(help="some random help string")

    help_text = Config.__argspec_schema__.help()
    assert "--path PATH <str>\n    some random help string" in help_text


def test_option_help_does_not_generate_short_by_default() -> None:
    class Config(ArgSpec):
        path: str = option(help="some random help string")

    help_text = Config.__argspec_schema__.help()
    # we use re.search instead of just ("-p" not in help_text) since "--path" will be there and also contains "-p"
    assert re.search(r"\b-p\b", help_text) is None


def test_flag_help_does_not_generate_short_by_default() -> None:
    class Config(ArgSpec):
        verbose: bool = flag(help="some random help string")

    help_text = Config.__argspec_schema__.help()
    assert re.search(r"\b-v\b", help_text) is None


def test_help_output_includes_automatic_flag_negators() -> None:
    class Config(ArgSpec):
        verbose: bool = flag(True)

    help_text = Config.__argspec_schema__.help()
    assert "false: --no-verbose" in help_text


def test_help_output_includes_flag_negators() -> None:
    class Config(ArgSpec):
        verbose: bool = flag(True, negators=("--quiet",))

    help_text = Config.__argspec_schema__.help()
    assert "false: --quiet" in help_text


def test_help_output_includes_option_aliases() -> None:
    class Config(ArgSpec):
        path: str = option(aliases=["-a", "-b", "--some-path"])

    help_text = Config.__argspec_schema__.help()
    assert "-a, -b, --some-path, --path" in help_text


def test_help_output_includes_flag_aliases() -> None:
    class Config(ArgSpec):
        verbose: bool = flag(aliases=["-a", "-b", "--alt-verbose"])

    help_text = Config.__argspec_schema__.help()
    assert "-a, -b, --alt-verbose, --verbose" in help_text


def test_help_output_includes_short_option_aliases() -> None:
    class Config(ArgSpec):
        path: str = option(short=True)

    help_text = Config.__argspec_schema__.help()
    assert "-p, --path" in help_text


def test_help_output_includes_help_flag() -> None:
    class Config(ArgSpec):
        verbose: bool = flag()

    help_text = Config.__argspec_schema__.help()
    assert "-h, --help" in help_text


def test_help_output_includes_help_flag_even_with_h_shadowed() -> None:
    class Config(ArgSpec):
        host: str = option(short=True)

    help_text = Config.__argspec_schema__.help()
    assert "-h, --host" in help_text
    assert "-h, --help" not in help_text
    assert "--help" in help_text


def test_help_output_includes_help_flag_even_with_help_shadowed() -> None:
    class Config(ArgSpec):
        help: int = option(help="do something")

    help_text = Config.__argspec_schema__.help()
    assert "-h, --help" not in help_text  # -h isn't aliased
    assert "--help HELP <int>\n    do something" in help_text
    assert "-h\n    Print this message and exit" in help_text


def test_help_output_does_not_include_help_flag_when_both_h_and_help_are_shadowed() -> None:
    class Config(ArgSpec):
        host: str = option(short=True)
        help: int = option(help="do something")

    help_text = Config.__argspec_schema__.help()
    assert "-h, --host" in help_text
    assert "--help HELP <int>\n    do something" in help_text
    assert "Print this message and exit" not in help_text


@pytest.mark.parametrize(
    "argv",
    [
        # help flags on their own
        ["-h"],
        ["--help"],
        # help flags with other arguments
        ["-h", "--verbose"],
        ["--help", "--verbose"],
        # help flags with invalid arguments
        ["-h", "3"],
        ["--help", "3"],
    ],
)
def test_passing_help_flag_prints_usage(argv: list[str]) -> None:
    class Config(ArgSpec):
        verbose: bool = flag()

    s = StringIO()
    with redirect_stderr(s):
        try:
            Config.from_argv(argv)
        except SystemExit:
            assert s.getvalue() == Config.__argspec_schema__.help() + "\n"
        else:
            assert False


@pytest.mark.parametrize(
    "argv",
    [
        # help flags on their own
        ["--help"],
        # help flags with other arguments
        ["--help", "--verbose"],
        # help flags with invalid arguments
        ["--help", "3"],
    ],
)
def test_passing_help_flag_prints_usage_when_h_is_shadowed(argv: list[str]) -> None:
    class Config(ArgSpec):
        host: str = option(short=True)
        verbose: bool = flag()

    s = StringIO()
    with redirect_stderr(s):
        try:
            Config.from_argv(argv)
        except SystemExit:
            assert s.getvalue() == Config.__argspec_schema__.help() + "\n"
        else:
            assert False


def test_passing_h_flag_does_not_print_usage_when_h_is_shadowed() -> None:
    class Config(ArgSpec):
        host: str = option(short=True)
        verbose: bool = flag()

    argv = ["-h", "localhost", "--verbose"]
    config = Config.from_argv(argv)

    assert config.host == "localhost"
    assert config.verbose


@pytest.mark.parametrize(
    "argv",
    [
        # help flags on their own
        ["-h"],
        # help flags with other arguments
        ["-h", "--verbose"],
        # help flags with invalid arguments
        ["-h", "3"],
    ],
)
def test_passing_h_flag_prints_usage_when_help_is_shadowed(argv: list[str]) -> None:
    class Config(ArgSpec):
        help: int = option()
        verbose: bool = flag()

    s = StringIO()
    with redirect_stderr(s):
        try:
            Config.from_argv(argv)
        except SystemExit:
            assert s.getvalue() == Config.__argspec_schema__.help() + "\n"
        else:
            assert False


def test_passing_help_flag_does_not_print_usage_when_help_is_shadowed() -> None:
    class Config(ArgSpec):
        help: int = option()
        verbose: bool = flag()

    argv = ["--help", "7", "--verbose"]
    config = Config.from_argv(argv)

    assert config.help == 7
    assert config.verbose


def test_passing_help_flag_does_not_print_usage_when_help_and_h_are_shadowed() -> None:
    class Config(ArgSpec):
        host: str = option(short=True)
        help: int = option()
        verbose: bool = flag()

    argv = ["-h", "localhost", "--help", "7", "--verbose"]
    config = Config.from_argv(argv)

    assert config.host == "localhost"
    assert config.help == 7
    assert config.verbose


def test_shadowing_help_flag_with_short_alias() -> None:
    class Config(ArgSpec):
        help: int = option(short=True)
        verbose: bool = flag()

    argv = ["-h", "7", "--verbose"]
    config = Config.from_argv(argv)

    assert config.help == 7
    assert config.verbose


def test_correct_type_hints_in_help() -> None:
    class Config(ArgSpec):
        ports: list[int] = option(help="list of ports")
        path: Path = positional(help="path to file")

    help_text = Config.__argspec_schema__.help()
    assert "--ports PORTS <list[int]>\n    list of ports" in help_text
    assert "Arguments:\n    PATH <Path>\n    path to file" in help_text
