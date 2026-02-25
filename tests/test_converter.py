from collections.abc import Iterator
from dataclasses import dataclass
import json

from argspec import ArgSpec, option, positional


def test_schema_arity_with_converter() -> None:
    class Args(ArgSpec):
        metadata: dict[str, int] = option(converter=json.loads)

    schema = Args.__argspec_schema__
    assert schema.nargs_for("metadata") == 1


def test_json_converter_option() -> None:
    class Args(ArgSpec):
        metadata: dict[str, int] = option(converter=json.loads)

    args = Args.from_argv(["--metadata", '{"foo": 1, "bar": 2}'])
    assert args.metadata == {"foo": 1, "bar": 2}


def test_json_converter_positional() -> None:
    class Args(ArgSpec):
        metadata: dict[str, int] = positional(converter=json.loads)

    args = Args.from_argv(['{"foo": 1, "bar": 2}'])
    assert args.metadata == {"foo": 1, "bar": 2}


def test_split_converter_option() -> None:
    class Args(ArgSpec):
        values: list[int] = option(converter=lambda s: s.split(","))

    args = Args.from_argv(["--values", "1,2,3"])
    assert args.values == [1, 2, 3]


def test_split_converter_positional() -> None:
    class Args(ArgSpec):
        values: list[int] = positional(converter=lambda s: s.split(","))

    args = Args.from_argv(["1,2,3"])
    assert args.values == [1, 2, 3]


def test_complex_converter_option() -> None:
    @dataclass
    class Point:
        x: float
        y: float

    class Args(ArgSpec):
        point: Point = option(converter=lambda s: Point(*[float(t) for t in s.split(",")]))

    args = Args.from_argv(["--point", "1.0,2.0"])
    assert args.point == Point(1.0, 2.0)


def test_complex_converter_positional() -> None:
    @dataclass
    class Point:
        x: float
        y: float

    class Args(ArgSpec):
        point: Point = positional(converter=lambda s: Point(*[float(t) for t in s.split(",")]))

    args = Args.from_argv(["1.0,2.0"])
    assert args.point == Point(1.0, 2.0)


def test_complex_converter_level2_option() -> None:
    @dataclass
    class Point:
        x: float
        y: float

    def _make_points(s: str) -> Iterator[Point]:
        """Convert 1,2;3,4;5,6 into [Point(1,2), Point(3,4), Point(5,6)]"""
        for point in s.split(";"):
            yield Point(*[float(t) for t in point.split(",")])

    class Args(ArgSpec):
        points: tuple[Point, ...] = option(converter=_make_points)

    args = Args.from_argv(["--points", "1.0,2.0;3.0,4.0;5.0,6.0"])
    assert args.points == (Point(1.0, 2.0), Point(3.0, 4.0), Point(5.0, 6.0))


def test_complex_converter_level2_positional() -> None:
    @dataclass
    class Point:
        x: float
        y: float

    def _make_points(s: str) -> Iterator[Point]:
        """Convert 1,2;3,4;5,6 into [Point(1,2), Point(3,4), Point(5,6)]"""
        for point in s.split(";"):
            yield Point(*[float(t) for t in point.split(",")])

    class Args(ArgSpec):
        points: tuple[Point, ...] = positional(converter=_make_points)

    args = Args.from_argv(["1.0,2.0;3.0,4.0;5.0,6.0"])
    assert args.points == (Point(1.0, 2.0), Point(3.0, 4.0), Point(5.0, 6.0))
