"""Tests for Either flat_map."""

from pyfect import either, pipe
from pyfect.either import Left, Right


def parse_int(s: str) -> either.Either[int, str]:
    try:
        return either.right(int(s))
    except ValueError:
        return either.left("not a number")


def test_flat_map_transforms_right() -> None:
    result = pipe(either.right("42"), either.flat_map(parse_int))
    assert result == Right(42)


def test_flat_map_returns_left_on_failure() -> None:
    result = pipe(either.right("xx"), either.flat_map(parse_int))
    assert result == Left("not a number")


def test_flat_map_passes_left_through() -> None:
    e: either.Either[str, str] = either.left("oops")
    result = pipe(e, either.flat_map(parse_int))
    assert result == Left("oops")


def test_flat_map_chains() -> None:
    result = pipe(
        either.right("42"),
        either.flat_map(parse_int),
        either.flat_map(lambda n: either.right(n * 2) if n > 0 else either.left("non-positive")),
    )
    assert result == Right(84)


def test_flat_map_short_circuits_on_left() -> None:
    result = pipe(
        either.right("xx"),
        either.flat_map(parse_int),
        either.flat_map(lambda n: either.right(n * 2)),
    )
    assert result == Left("not a number")
