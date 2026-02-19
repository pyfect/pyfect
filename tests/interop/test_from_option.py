"""Tests for effect.from_option."""

from pyfect import effect, option, pipe


def test_from_option_some_succeeds() -> None:
    result = effect.run_sync_exit(pipe(option.some(42), effect.from_option(lambda: "not found")))
    assert isinstance(result, effect.Success)
    assert result.value == 42  # noqa: PLR2004


def test_from_option_nothing_fails() -> None:
    result = effect.run_sync_exit(pipe(option.nothing(), effect.from_option(lambda: "not found")))
    assert isinstance(result, effect.Failure)
    assert result.error == "not found"


def test_from_option_error_thunk_not_called_for_some() -> None:
    called = False

    def error() -> str:
        nonlocal called
        called = True
        return "not found"

    effect.run_sync_exit(pipe(option.some(42), effect.from_option(error)))
    assert not called


def test_from_option_error_thunk_called_for_nothing() -> None:
    called = False

    def error() -> str:
        nonlocal called
        called = True
        return "not found"

    effect.run_sync_exit(pipe(option.nothing(), effect.from_option(error)))
    assert called
