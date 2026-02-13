"""Tests for Either zip_with."""

from pyfect import either
from pyfect.either import Left, Right


def test_zip_with_two_rights() -> None:
    result = either.zip_with(either.right("John"), either.right(25), lambda name, age: (name, age))
    assert result == Right(("John", 25))


def test_zip_with_left_first() -> None:
    result = either.zip_with(
        either.left("no name"), either.right(25), lambda name, age: (name, age)
    )
    assert result == Left("no name")


def test_zip_with_left_second() -> None:
    result = either.zip_with(
        either.right("John"), either.left("no age"), lambda name, age: (name, age)
    )
    assert result == Left("no age")


def test_zip_with_both_left_returns_first() -> None:
    result = either.zip_with(either.left("first"), either.left("second"), lambda a, b: (a, b))
    assert result == Left("first")


def test_zip_with_transforms_values() -> None:
    result = either.zip_with(either.right(2), either.right(3), lambda a, b: a * b)
    assert result == Right(6)
