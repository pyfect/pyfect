"""Tests for Exit core types and type guards."""

from pyfect import exit as exit_module


def test_succeed_creates_success() -> None:
    """succeed should create a Success instance."""
    result = exit_module.succeed(42)
    assert isinstance(result, exit_module.Success)
    assert result.value == 42  # noqa: PLR2004


def test_fail_creates_failure() -> None:
    """fail should create a Failure instance."""
    result = exit_module.fail("error")
    assert isinstance(result, exit_module.Failure)
    assert result.error == "error"


def test_is_success_returns_true_for_success() -> None:
    """is_success should return True for Success values."""
    result = exit_module.succeed(42)
    assert exit_module.is_success(result)


def test_is_success_returns_false_for_failure() -> None:
    """is_success should return False for Failure values."""
    result = exit_module.fail("error")
    assert not exit_module.is_success(result)


def test_is_failure_returns_true_for_failure() -> None:
    """is_failure should return True for Failure values."""
    result = exit_module.fail("error")
    assert exit_module.is_failure(result)


def test_is_failure_returns_false_for_success() -> None:
    """is_failure should return False for Success values."""
    result = exit_module.succeed(42)
    assert not exit_module.is_failure(result)


def test_is_success_narrows_type() -> None:
    """is_success should narrow the type for type checkers."""
    result: exit_module.Exit[int, str] = exit_module.succeed(42)

    if exit_module.is_success(result):
        # Type checker should know result is Success[int, str] here
        value: int = result.value
        assert value == 42  # noqa: PLR2004


def test_is_failure_narrows_type() -> None:
    """is_failure should narrow the type for type checkers."""
    result: exit_module.Exit[int, str] = exit_module.fail("error")

    if exit_module.is_failure(result):
        # Type checker should know result is Failure[int, str] here
        error: str = result.error
        assert error == "error"
