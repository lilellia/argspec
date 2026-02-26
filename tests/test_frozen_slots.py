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


def test_slots_by_default() -> None:
    class Config(ArgSpec):
        x: str = positional()
        y: int = option()

    config = Config(x="initial", y=0)

    assert getattr(config, "__slots__", ()) == ("x", "y")
    assert not hasattr(config, "__dict__")


def test_slots_can_be_disabled() -> None:
    class Config(ArgSpec, slots=False):
        x: str = positional()
        y: int = option()

    config = Config(x="initial", y=0)

    assert getattr(config, "__slots__", ()) == ()  # Make sure we don't expose any slots
    assert hasattr(config, "__dict__")
    assert {"x", "y"}.issubset(config.__dict__)

    # We should still inherit the parent's slots, even though we're not exposing them ourselves.
    assert hasattr(config, "__ARGSPEC_VALIDATED__")


def test_slots_and_frozen_can_be_disabled_simultaneously() -> None:
    class Config(ArgSpec, frozen=False, slots=False):
        x: str = positional()
        y: int = option()

    config = Config(x="initial", y=0)

    # make sure we're a nonslotted class
    assert getattr(config, "__slots__", ()) == ()
    assert hasattr(config, "__dict__")

    # make sure we're not frozen
    config.x = "new value"
    assert config.x == "new value"
