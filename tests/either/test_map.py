"""Tests for Either map and map_left."""

from pyfect import either, pipe
from pyfect.either import Left, Right

# ============================================================================
# map
# ============================================================================


def test_map_transforms_right() -> None:
    result = pipe(either.right(1), either.map_(lambda x: x + 1))
    assert result == Right(2)


def test_map_passes_left_through() -> None:
    e: either.Either[int, str] = either.left("oops")
    result = pipe(e, either.map_(lambda x: x + 1))
    assert result == Left("oops")


def test_map_changes_right_type() -> None:
    result = pipe(either.right(42), either.map_(str))
    assert result == Right("42")


# ============================================================================
# map_left
# ============================================================================


def test_map_left_transforms_left() -> None:
    result = pipe(either.left("oops"), either.map_left(lambda s: s + "!"))
    assert result == Left("oops!")


def test_map_left_passes_right_through() -> None:
    e: either.Either[int, str] = either.right(1)
    result = pipe(e, either.map_left(lambda s: s + "!"))
    assert result == Right(1)


def test_map_left_changes_left_type() -> None:
    result = pipe(either.left("42"), either.map_left(int))
    assert result == Left(42)


# ============================================================================
# map_both
# ============================================================================


def test_map_both_transforms_right() -> None:
    result = pipe(
        either.right(1), either.map_both(on_right=lambda n: n + 1, on_left=lambda s: s + "!")
    )
    assert result == Right(2)


def test_map_both_transforms_left() -> None:
    result = pipe(
        either.left("oops"), either.map_both(on_right=lambda n: n + 1, on_left=lambda s: s + "!")
    )
    assert result == Left("oops!")


def test_map_both_changes_both_types() -> None:
    result = pipe(either.right(42), either.map_both(on_right=str, on_left=int))
    assert result == Right("42")
