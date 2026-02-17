"""Tests for option.get_or_raise."""

from typing import NoReturn

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


def test_get_or_raise_noreturn_type_hint() -> None:
    """get_or_raise should have NoReturn type when input is Nothing.

    This test validates the type signature - the actual execution will raise.
    """
    with pytest.raises(ValueError):  # noqa: PT011
        # Type checker should infer this as NoReturn
        _result: NoReturn = option.get_or_raise(option.nothing())
