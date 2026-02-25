from pathlib import Path

import pytest

from argspec import ArgSpec, positional


def test_basic_direct_instantiation() -> None:
    class Config(ArgSpec):
        path: Path = positional()

    config = Config(Path.home())
    assert config.path == Path.home()


def test_basic_direct_instantiation_invalid_type() -> None:
    class Config(ArgSpec):
        path: Path = positional()

    with pytest.raises(TypeError):
        Config(12)  # type: ignore[arg-type]


def test_basic_direct_instantiation_missing_required() -> None:
    class Config(ArgSpec):
        path: Path = positional()

    with pytest.raises(TypeError):
        Config()


def test_basic_direct_instantiation_filling_defaults() -> None:
    class Config(ArgSpec):
        x: int = positional(1)
        y: int = positional(2)
        z: int = positional(3)

    config = Config(x=12, z=-178)
    assert config.x == 12
    assert config.y == 2
    assert config.z == -178
