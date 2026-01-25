import os
from typing import Any

from .metadata import MISSING


class readenv:
    """A zero-argument callable that returns the value of an environment variable when called."""

    def __init__(self, key: str, default: Any = MISSING) -> None:
        self.key = key
        self.default = default

    def __call__(self) -> Any:
        return os.environ.get(self.key, self.default)
