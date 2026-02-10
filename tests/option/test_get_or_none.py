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
