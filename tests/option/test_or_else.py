"""Tests for option.or_else."""

from pyfect import option, pipe


def test_or_else_some_returns_original() -> None:
    result = pipe(option.some(42), option.or_else(lambda: option.some(0)))
    assert option.is_some(result)
    assert result.value == 42  # noqa: PLR2004


def test_or_else_nothing_returns_alternative() -> None:
    result = pipe(option.nothing(), option.or_else(lambda: option.some(0)))
    assert option.is_some(result)
    assert result.value == 0


def test_or_else_nothing_alternative_also_nothing() -> None:
    result = pipe(option.nothing(), option.or_else(option.nothing))
    assert option.is_nothing(result)


def test_or_else_alternative_not_called_for_some() -> None:
    called = False

    def alternative() -> option.Option[int]:
        nonlocal called
        called = True
        return option.some(0)

    pipe(option.some(42), option.or_else(alternative))
    assert not called


def test_or_else_alternative_called_for_nothing() -> None:
    called = False

    def alternative() -> option.Option[int]:
        nonlocal called
        called = True
        return option.some(0)

    pipe(option.nothing(), option.or_else(alternative))
    assert called
