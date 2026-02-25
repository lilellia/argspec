from argspec import ArgSpec, option, positional


def test_shared_mutable_defaults_arent_actually_shared_positional() -> None:
    class Config(ArgSpec):
        field: list[int] = positional([])

    config1 = Config.from_argv([])
    config2 = Config.from_argv([])

    assert config1.field == []
    assert config2.field == []

    config1.field.append(1)

    assert config1.field == [1]
    assert config2.field == []


def test_shared_mutable_defaults_arent_actually_shared_option() -> None:
    class Config(ArgSpec):
        field: list[int] = option([])

    config1 = Config.from_argv([])
    config2 = Config.from_argv([])

    assert config1.field == []
    assert config2.field == []

    config1.field.append(1)

    assert config1.field == [1]
    assert config2.field == []
