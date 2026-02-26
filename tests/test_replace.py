import pytest

from argspec import ArgSpec, option, positional


def test_basic_replace() -> None:
    class Config(ArgSpec):
        x: str = positional()
        y: int = option()

    config = Config(x="initial", y=0)

    new = config.replace(x="new value", y=1)

    assert new.x == "new value"
    assert new.y == 1


def test_replace_with_invalid_key_is_error() -> None:
    class Config(ArgSpec):
        x: str = positional()
        y: int = option()

    config = Config(x="initial", y=0)

    with pytest.raises(TypeError):
        config.replace(z="new value")


def test_replace_with_no_kwargs_makes_no_changes() -> None:
    class Config(ArgSpec):
        x: str = positional()
        y: int = option()

    config = Config(x="initial", y=0)

    new = config.replace()

    assert new == config


def test_replace_with_incollapsible_type_is_error() -> None:
    class Config(ArgSpec):
        x: str = positional()
        y: int = option()

    config = Config(x="initial", y=0)

    with pytest.raises(ValueError):
        config.replace(y="invalid")


def test_replace_with_collapsible_type_is_collapsed() -> None:
    class Config(ArgSpec):
        x: str = positional()
        y: int = option()

    config = Config(x="initial", y=0)

    new = config.replace(y="1")

    assert new.y == 1


def test_replace_with_validators() -> None:
    class Config(ArgSpec):
        x: str = positional()
        y: int = option(validator=lambda y: y > 0)

    config = Config(x="initial", y=1)

    with pytest.raises(ValueError):
        config.replace(y=0)


def test_replace_with_bypass_validators() -> None:
    class Config(ArgSpec):
        x: str = positional()
        y: int = option(validator=lambda y: y > 0)

    config = Config(x="initial", y=1)

    new = config.replace(y="-1", __ARGSPEC_SKIP_VALIDATION__=True)

    assert new.y == "-1"  # type: ignore[comparison-overlap]
