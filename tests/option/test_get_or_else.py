"""Tests for option.get_or_else."""

from pyfect import option, pipe


def test_get_or_else_some_returns_value() -> None:
    result = pipe(option.some(42), option.get_or_else(lambda: 0))
    assert result == 42  # noqa: PLR2004


def test_get_or_else_nothing_returns_default() -> None:
    result = pipe(option.nothing(), option.get_or_else(lambda: 0))
    assert result == 0


def test_get_or_else_default_not_called_for_some() -> None:
    called = False

    def default() -> int:
        nonlocal called
        called = True
        return 0

    pipe(option.some(42), option.get_or_else(default))
    assert not called


def test_get_or_else_default_called_for_nothing() -> None:
    called = False

    def default() -> int:
        nonlocal called
        called = True
        return 0

    pipe(option.nothing(), option.get_or_else(default))
    assert called
