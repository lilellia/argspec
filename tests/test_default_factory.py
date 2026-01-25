import pytest

from argspec import ArgSpec, ArgumentSpecError, option, positional


def test_default_and_default_factory_is_error_positional() -> None:
    with pytest.raises(ArgumentSpecError, match="Cannot specify both default and default_factory"):

        class Config(ArgSpec):
            value: str = positional("foo", default_factory=lambda: "bar")


def test_default_and_default_factory_is_error_option() -> None:
    with pytest.raises(ArgumentSpecError, match="Cannot specify both default and default_factory"):

        class Config(ArgSpec):
            value: str = option("foo", default_factory=lambda: "bar")


def test_default_factory_fallback_correctly_typed_positional() -> None:
    class Config(ArgSpec):
        value: str = positional(default_factory=lambda: "bar")

    config = Config.from_argv([])
    assert config.value == "bar"


def test_default_factory_fallback_incorrectly_typed_positional() -> None:
    class Config(ArgSpec):
        value: int = positional(default_factory=lambda: "1")

    config = Config.from_argv([])
    assert config.value == 1
    assert isinstance(config.value, int)


def test_default_factory_fallback_correctly_typed_option() -> None:
    class Config(ArgSpec):
        value: str = option(default_factory=lambda: "bar")

    config = Config.from_argv([])
    assert config.value == "bar"


def test_default_factory_fallback_incorrectly_typed_option() -> None:
    class Config(ArgSpec):
        value: int = option(default_factory=lambda: "1")

    config = Config.from_argv([])
    assert config.value == 1
    assert isinstance(config.value, int)
