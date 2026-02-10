"""Tests for option.get_or_raise."""

import pytest

from pyfect import option, pipe


def test_get_or_raise_some_returns_value() -> None:
    result = pipe(option.some(42), option.get_or_raise)
    assert result == 42  # noqa: PLR2004


def test_get_or_raise_nothing_raises() -> None:
    with pytest.raises(ValueError, match="get_or_raise called on Nothing"):
        pipe(option.nothing(), option.get_or_raise)


def test_get_or_raise_preserves_value_type() -> None:
    result = pipe(option.some("hello"), option.get_or_raise)
    assert result == "hello"
