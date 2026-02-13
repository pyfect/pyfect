"""Tests for Either core types, constructors, and guards."""

from dataclasses import FrozenInstanceError

import pytest

from pyfect import either
from pyfect.either import Left, Right


def test_right_holds_value() -> None:
    e = either.right(42)
    assert either.is_right(e)
    assert e.value == 42  # type: ignore[union-attr]  # noqa: PLR2004


def test_left_holds_value() -> None:
    e = either.left("oops")
    assert either.is_left(e)
    assert e.value == "oops"  # type: ignore[union-attr]


def test_right_is_not_left() -> None:
    assert not either.is_left(either.right(1))


def test_left_is_not_right() -> None:
    assert not either.is_right(either.left("error"))


def test_right_is_frozen() -> None:
    e = either.right(1)
    with pytest.raises(FrozenInstanceError):
        e.value = 2  # type: ignore[misc]


def test_left_is_frozen() -> None:
    e = either.left("oops")
    with pytest.raises(FrozenInstanceError):
        e.value = "other"  # type: ignore[misc]


def test_pattern_match_right() -> None:
    e = either.right(42)
    match e:
        case Right(value):
            assert value == 42  # noqa: PLR2004
        case Left():
            pytest.fail("Expected Right")


def test_pattern_match_left() -> None:
    e = either.left("oops")
    match e:
        case Left(value):
            assert value == "oops"
        case Right():
            pytest.fail("Expected Left")
