from argspec import ArgSpec, positional


def test_track_skip_validation_is_normally_true() -> None:
    class Args(ArgSpec):
        x: int = positional()

    args = Args(x=1)
    assert args.__ARGSPEC_VALIDATED__  # type: ignore[attr-defined]


def test_track_skip_validation_when_explicitly_false() -> None:
    class Args(ArgSpec):
        x: int = positional()

    args = Args(x="1", __ARGSPEC_SKIP_VALIDATION__=True)  # type: ignore[arg-type, call-arg]
    assert not args.__ARGSPEC_VALIDATED__  # type: ignore[attr-defined]


def test_track_skip_validation_via_replace() -> None:
    class Args(ArgSpec):
        x: int = positional()

    args = Args(x=1)
    assert args.__ARGSPEC_VALIDATED__  # type: ignore[attr-defined]

    new1 = args.replace(x=-2)
    assert new1.__ARGSPEC_VALIDATED__  # type: ignore[attr-defined]

    new2 = args.replace(x="-2", __ARGSPEC_SKIP_VALIDATION__=True)
    assert not new2.__ARGSPEC_VALIDATED__  # type: ignore[attr-defined]


def test_track_skip_validation_can_be_cleaned() -> None:
    class Args(ArgSpec):
        x: int = positional()

    args = Args(x="1", __ARGSPEC_SKIP_VALIDATION__=True)  # type: ignore[arg-type, call-arg]
    assert not args.__ARGSPEC_VALIDATED__  # type: ignore[attr-defined]

    new = args.replace(x=2)
    assert new.__ARGSPEC_VALIDATED__  # type: ignore[attr-defined]
