import os

import pytest

from argspec import ArgSpec, ArgumentError, option, readenv


def test_readenv_fallback() -> None:
    class Config(ArgSpec):
        api_key: str = option(default_factory=readenv("SERVICE_API_KEY"), help="the API key for the service")

    os.environ["SERVICE_API_KEY"] = "environment value for service api key"
    config = Config.from_argv([])
    assert config.api_key == "environment value for service api key"


def test_readenv_is_not_overwritten() -> None:
    class Config(ArgSpec):
        api_key: str = option(default_factory=readenv("SERVICE_API_KEY"), help="the API key for the service")

    os.environ["SERVICE_API_KEY"] = "environment value for service api key"

    argv = ["--api-key", "command line value for service api key"]
    config = Config.from_argv(argv)
    assert config.api_key == "command line value for service api key"


def test_readenv_raises_error_when_no_default_and_not_provided() -> None:
    class Config(ArgSpec):
        api_key: str = option(default_factory=readenv("SERVICE_API_KEY"), help="the API key for the service")

    os.environ.pop("SERVICE_API_KEY", None)
    with pytest.raises(ArgumentError):
        Config._from_argv([])


def test_readenv_obeys_fallback_when_not_provided() -> None:
    class Config(ArgSpec):
        api_key: str = option(
            default_factory=readenv("SERVICE_API_KEY", "fallback value"), help="the API key for the service"
        )

    os.environ.pop("SERVICE_API_KEY", None)
    config = Config._from_argv([])
    assert config.api_key == "fallback value"


def test_readenv_prioritises_command_line() -> None:
    class Config(ArgSpec):
        api_key: str = option(
            default_factory=readenv("SERVICE_API_KEY", "fallback value"), help="the API key for the service"
        )

    os.environ.pop("SERVICE_API_KEY", None)
    argv = ["--api-key", "command line value for service api key"]
    config = Config._from_argv(argv)
    assert config.api_key == "command line value for service api key"


def test_help_message_for_readenv_when_not_set_and_no_default() -> None:
    class Config(ArgSpec):
        api_key: str = option(default_factory=readenv("SERVICE_API_KEY"), help="the API key for the service")

    os.environ.pop("SERVICE_API_KEY", None)
    help_text = Config.__argspec_schema__.help()
    assert "(default: $SERVICE_API_KEY (currently: <unset>))" in help_text


def test_help_message_for_readenv_when_not_set_but_default() -> None:
    class Config(ArgSpec):
        api_key: str = option(
            default_factory=readenv("SERVICE_API_KEY", "fallback value"), help="the API key for the service"
        )

    os.environ.pop("SERVICE_API_KEY", None)
    help_text = Config.__argspec_schema__.help()
    assert "(default: $SERVICE_API_KEY or 'fallback value' (currently: 'fallback value'))" in help_text


def test_help_message_for_readenv_when_set_and_default() -> None:
    class Config(ArgSpec):
        api_key: str = option(
            default_factory=readenv("SERVICE_API_KEY", "fallback value"), help="the API key for the service"
        )

    os.environ["SERVICE_API_KEY"] = "environment value for service api key"
    help_text = Config.__argspec_schema__.help()
    expected = "(default: $SERVICE_API_KEY or 'fallback value' (currently: 'environment value for service api key'))"
    assert expected in help_text


def test_help_message_for_readenv_when_set_but_no_default() -> None:
    class Config(ArgSpec):
        api_key: str = option(default_factory=readenv("SERVICE_API_KEY"), help="the API key for the service")

    os.environ["SERVICE_API_KEY"] = "environment value for service api key"
    help_text = Config.__argspec_schema__.help()
    expected = "(default: $SERVICE_API_KEY (currently: 'environment value for service api key'))"
    assert expected in help_text
