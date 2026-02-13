"""Tests for option.filter."""

from pyfect import option, pipe


def test_filter_some_passes_predicate() -> None:
    result = pipe(option.some(42), option.filter(lambda x: x > 0))
    assert option.is_some(result)
    assert result.value == 42  # noqa: PLR2004


def test_filter_some_fails_predicate() -> None:
    result = pipe(option.some(-1), option.filter(lambda x: x > 0))
    assert option.is_nothing(result)


def test_filter_nothing_returns_nothing() -> None:
    result = pipe(option.nothing(), option.filter(lambda x: x > 0))
    assert option.is_nothing(result)


def test_filter_preserves_singleton() -> None:
    result = pipe(option.nothing(), option.filter(lambda x: x > 0))
    assert result is option.NOTHING


def test_filter_does_not_call_predicate_on_nothing() -> None:
    called = False

    def predicate(x: int) -> bool:
        nonlocal called
        called = True
        return True

    pipe(option.nothing(), option.filter(predicate))
    assert not called
