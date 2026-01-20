import re

from argspec import ArgSpec, flag, option, positional


def test_positional_help() -> None:
    class Config(ArgSpec):
        path: str = positional(help="some random help string")

    help_text = Config.__argspec_schema__.help()
    assert "some random help string" in help_text


def test_option_help() -> None:
    class Config(ArgSpec):
        path: str = option(help="some random help string")

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
    assert "--path" in help_text


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
