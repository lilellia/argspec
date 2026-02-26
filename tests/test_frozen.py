import pytest

from argspec import ArgSpec, option, positional


def test_frozen_by_default() -> None:
    class Config(ArgSpec):
        x: str = positional()
        y: int = option()

    config = Config(x="initial", y=0)

    assert config.x == "initial"
    assert config.y == 0

    with pytest.raises(AttributeError):
        config.x = "new value"

    with pytest.raises(AttributeError):
        config.y = 1


def test_frozen_can_be_disabled() -> None:
    class Config(ArgSpec, frozen=False):
        x: str = positional()
        y: int = option()

    config = Config(x="initial", y=0)

    assert config.x == "initial"
    assert config.y == 0

    config.x = "new value"
    config.y = 1

    assert config.x == "new value"
    assert config.y == 1
