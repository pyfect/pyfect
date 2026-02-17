"""Tests for option.get_or_none."""

from pyfect import option, pipe


def test_get_or_none_some_returns_value() -> None:
    result = pipe(option.some(42), option.get_or_none)
    assert result == 42  # noqa: PLR2004


def test_get_or_none_nothing_returns_none() -> None:
    result = pipe(option.nothing(), option.get_or_none)
    assert result is None


def test_get_or_none_preserves_value_type() -> None:
    result = pipe(option.some("hello"), option.get_or_none)
    assert result == "hello"


def test_get_or_none_narrows_type_for_nothing() -> None:
    """get_or_none should narrow return type to None when input is Nothing."""
    # When we know it's Nothing, result type should be None
    result = option.get_or_none(option.nothing())
    assert result is None
