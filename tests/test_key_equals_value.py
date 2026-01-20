from pathlib import Path

import pytest

from argspec import ArgSpec, ArgumentError, flag, option, positional


def test_key_equals_value_basic() -> None:
    class Config(ArgSpec):
        path: Path = option()

    argv = ["--path=/path/to/file"]
    config = Config.from_argv(argv)

    assert config.path == Path("/path/to/file")


def test_short_key_equals_value_basic() -> None:
    class Config(ArgSpec):
        path: Path = option(short=True)

    argv = ["-p=/path/to/file"]
    config = Config.from_argv(argv)

    assert config.path == Path("/path/to/file")


def test_key_equals_value_invalid() -> None:
    class Config(ArgSpec):
        path: Path = option(Path("/path/to/file"))

    argv = ["--number=2"]
    with pytest.raises(ArgumentError):
        Config._from_argv(argv)


def test_key_equals_value_that_has_an_equal_sign() -> None:
    class Config(ArgSpec):
        metadata: str = option()

    argv = ["--metadata=key1=value1,key2=value2"]
    config = Config.from_argv(argv)

    assert config.metadata == "key1=value1,key2=value2"


def test_flag_equals_explicit_false_is_error() -> None:
    class Config(ArgSpec):
        verbose: bool = flag()

    argv = ["--verbose=false"]

    with pytest.raises(ArgumentError):
        Config._from_argv(argv)


def test_positional_with_equal_sign_does_not_get_split() -> None:
    class Config(ArgSpec):
        metadata: str = positional()

    argv = ["key1=value1,key2=value2"]
    config = Config.from_argv(argv)

    assert config.metadata == "key1=value1,key2=value2"


def test_key_equals_value_with_empty_value() -> None:
    class Config(ArgSpec):
        metadata: str = option()

    argv = ["--metadata="]
    config = Config.from_argv(argv)

    assert config.metadata == ""
