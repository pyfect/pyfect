"""Tests for the map_error combinator."""

import asyncio

import pytest

from pyfect import effect, pipe


def test_map_error_transforms_error() -> None:
    """Test that map_error transforms error values."""
    result = pipe(
        effect.fail("error"),
        effect.map_error(lambda e: f"Error: {e}"),
    )

    with pytest.raises(RuntimeError, match="Error: error"):
        effect.run_sync(result)


def test_map_error_preserves_success() -> None:
    """Test that map_error doesn't affect success values."""
    result = pipe(
        effect.succeed(42),
        effect.map_error(lambda e: f"Error: {e}"),
    )

    assert effect.run_sync(result) == 42  # noqa: PLR2004


def test_map_error_with_exception() -> None:
    """Test map_error with exception types."""

    class CustomError(Exception):
        def __init__(self, msg: str) -> None:
            self.msg = msg
            super().__init__(msg)

    result = pipe(
        effect.fail(ValueError("original")),
        effect.map_error(lambda e: CustomError(f"Wrapped: {e}")),
    )

    with pytest.raises(CustomError, match="Wrapped: original"):
        effect.run_sync(result)


def test_map_error_with_try_sync() -> None:
    """Test map_error with try_sync that fails."""

    def will_fail() -> int:
        msg = "computation failed"
        raise ValueError(msg)

    result = pipe(
        effect.try_sync(will_fail),
        effect.map_error(lambda e: f"Caught: {e}"),
    )

    exit_result = effect.run_sync_exit(result)

    match exit_result:
        case effect.Failure(error):
            assert error == "Caught: computation failed"
        case effect.Success(_):
            pytest.fail("Expected failure but got success")


def test_map_error_with_exit() -> None:
    """Test map_error with run_sync_exit."""
    result = pipe(
        effect.fail("original error"),
        effect.map_error(lambda e: f"transformed: {e}"),
    )

    exit_result = effect.run_sync_exit(result)

    match exit_result:
        case effect.Failure(error):
            assert error == "transformed: original error"
        case effect.Success(_):
            pytest.fail("Expected failure but got success")


def test_map_error_preserves_success_with_exit() -> None:
    """Test that map_error preserves success when using run_sync_exit."""
    result = pipe(
        effect.succeed(100),
        effect.map_error(lambda e: f"Error: {e}"),
    )

    exit_result = effect.run_sync_exit(result)

    match exit_result:
        case effect.Success(value):
            assert value == 100  # noqa: PLR2004
        case effect.Failure(_):
            pytest.fail("Expected success but got failure")


async def test_map_error_async() -> None:
    """Test map_error with async effects."""

    async def async_fail() -> int:
        await asyncio.sleep(0.01)
        msg = "async error"
        raise ValueError(msg)

    result = pipe(
        effect.try_async(async_fail),
        effect.map_error(lambda e: f"Async: {e}"),
    )

    exit_result = await effect.run_async_exit(result)

    match exit_result:
        case effect.Failure(error):
            assert error == "Async: async error"
        case effect.Success(_):
            pytest.fail("Expected failure but got success")


async def test_map_error_async_success() -> None:
    """Test map_error with successful async effects."""

    async def async_value() -> int:
        await asyncio.sleep(0.01)
        return 42

    result = pipe(
        effect.async_(async_value),
        effect.map_error(lambda e: f"Error: {e}"),
    )

    assert await effect.run_async(result) == 42  # noqa: PLR2004


def test_map_error_composition() -> None:
    """Test composing multiple map_error operations."""
    result = pipe(
        effect.fail("error"),
        effect.map_error(lambda e: f"1: {e}"),
        effect.map_error(lambda e: f"2: {e}"),
        effect.map_error(lambda e: f"3: {e}"),
    )

    exit_result = effect.run_sync_exit(result)

    match exit_result:
        case effect.Failure(error):
            assert error == "3: 2: 1: error"
        case effect.Success(_):
            pytest.fail("Expected failure but got success")


def test_map_error_type_change() -> None:
    """Test map_error can change error types."""

    class AError(Exception):
        pass

    class BError(Exception):
        pass

    result = pipe(
        effect.fail(AError("original")),
        effect.map_error(lambda e: BError(f"Converted: {e}")),
    )

    with pytest.raises(BError, match="Converted: original"):
        effect.run_sync(result)


def test_map_error_with_map() -> None:
    """Test map_error works alongside map."""
    result = pipe(
        effect.succeed(10),
        effect.map(lambda x: x * 2),  # 20
        effect.map_error(lambda e: f"Error: {e}"),
    )

    assert effect.run_sync(result) == 20  # noqa: PLR2004


def test_map_and_map_error_on_failure() -> None:
    """Test that map doesn't run on failure but map_error does."""
    executed_map = []
    executed_map_error = []

    def track_map(x: int) -> int:
        executed_map.append(x)
        return x * 2

    def track_map_error(e: str) -> str:
        executed_map_error.append(e)
        return f"Error: {e}"

    result = pipe(
        effect.fail("oops"),
        effect.map(track_map),
        effect.map_error(track_map_error),
    )

    effect.run_sync_exit(result)

    assert len(executed_map) == 0  # map was not called
    assert executed_map_error == ["oops"]  # map_error was called


def test_map_error_with_flat_map() -> None:
    """Test map_error with flat_map."""

    def may_fail(x: int) -> effect.Effect[int, str]:
        if x < 0:
            return effect.fail("negative number")
        return effect.succeed(x * 2)

    result = pipe(
        effect.succeed(-5),
        effect.flat_map(may_fail),
        effect.map_error(lambda e: f"Validation error: {e}"),
    )

    exit_result = effect.run_sync_exit(result)

    match exit_result:
        case effect.Failure(error):
            assert error == "Validation error: negative number"
        case effect.Success(_):
            pytest.fail("Expected failure but got success")


def test_map_error_is_lazy() -> None:
    """Test that map_error doesn't execute until run."""
    executed = []

    def track_transform(e: str) -> str:
        executed.append(e)
        return f"Transformed: {e}"

    result = pipe(
        effect.fail("error"),
        effect.map_error(track_transform),
    )

    # Not executed yet
    assert len(executed) == 0

    # Now run it
    effect.run_sync_exit(result)
    assert executed == ["error"]


def test_map_error_with_tap_error() -> None:
    """Test map_error works with tap_error."""
    tapped_errors = []
    transformed_errors = []

    result = pipe(
        effect.fail("original"),
        effect.tap_error(lambda e: effect.sync(lambda: tapped_errors.append(e))),
        effect.map_error(lambda e: f"transformed: {e}"),
        effect.tap_error(lambda e: effect.sync(lambda: transformed_errors.append(e))),
    )

    effect.run_sync_exit(result)

    assert tapped_errors == ["original"]
    assert transformed_errors == ["transformed: original"]


def test_map_error_string_to_exception() -> None:
    """Test map_error converting string errors to exceptions."""

    class AppError(Exception):
        def __init__(self, code: str, msg: str) -> None:
            self.code = code
            self.msg = msg
            super().__init__(f"{code}: {msg}")

    result = pipe(
        effect.fail("Something went wrong"),
        effect.map_error(lambda msg: AppError("ERR001", msg)),
    )

    with pytest.raises(AppError) as exc_info:
        effect.run_sync(result)

    assert exc_info.value.code == "ERR001"
    assert exc_info.value.msg == "Something went wrong"


def test_map_error_preserves_context() -> None:
    """Test that map_error preserves the context type R."""
    # Effect[int, str] -> map_error -> Effect[int, CustomError]

    class CustomError(Exception):
        pass

    result = pipe(
        effect.fail("error"),
        effect.map_error(CustomError),
    )

    with pytest.raises(CustomError, match="error"):
        effect.run_sync(result)


async def test_map_error_async_exception_transform() -> None:
    """Test map_error with async exception transformation."""

    class NetworkError(Exception):
        pass

    async def async_operation() -> int:
        await asyncio.sleep(0.01)
        msg = "connection timeout"
        raise TimeoutError(msg)

    result = pipe(
        effect.try_async(async_operation),
        effect.map_error(lambda e: NetworkError(f"Network: {e}")),
    )

    with pytest.raises(NetworkError, match="Network: connection timeout"):
        await effect.run_async(result)


def test_map_error_real_world_example() -> None:
    """Test a real-world example with validation."""

    class ValidationError(Exception):
        def __init__(self, field: str, message: str) -> None:
            self.field = field
            self.message = message
            super().__init__(f"{field}: {message}")

    def validate_age(age: int) -> effect.Effect[int, str]:
        if age < 0:
            return effect.fail("age cannot be negative")
        if age > 150:  # noqa: PLR2004
            return effect.fail("age is unrealistic")
        return effect.succeed(age)

    result = pipe(
        effect.succeed(-5),
        effect.flat_map(validate_age),
        effect.map_error(lambda msg: ValidationError("age", msg)),
    )

    with pytest.raises(ValidationError) as exc_info:
        effect.run_sync(result)

    assert exc_info.value.field == "age"
    assert exc_info.value.message == "age cannot be negative"


def test_map_error_exception_chain() -> None:
    """Test that map_error preserves exception chain."""

    class WrappedError(Exception):
        pass

    def will_fail() -> int:
        msg = "original error"
        raise ValueError(msg)

    result = pipe(
        effect.try_sync(will_fail),
        effect.map_error(lambda e: WrappedError(f"Wrapped: {e}")),
    )

    with pytest.raises(WrappedError) as exc_info:
        effect.run_sync(result)

    # Check that the exception chain is preserved
    assert exc_info.value.__cause__ is not None
    assert isinstance(exc_info.value.__cause__, ValueError)
    assert str(exc_info.value.__cause__) == "original error"
