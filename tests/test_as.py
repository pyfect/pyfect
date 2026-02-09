"""Tests for the as_ combinator."""

import asyncio

import pytest

from pyfect import effect, pipe


def test_as_replaces_value() -> None:
    """Test that as_ replaces the success value with a constant."""
    eff = effect.succeed(42)
    replaced = effect.as_("done")(eff)
    result = effect.run_sync(replaced)
    assert result == "done"


def test_as_with_pipe() -> None:
    """Test that as_ works with pipe for composition."""
    result = pipe(
        effect.succeed(100),
        effect.as_("replaced"),
    )
    assert effect.run_sync(result) == "replaced"


def test_as_ignores_original_value() -> None:
    """Test that as_ ignores the original value."""
    result = pipe(
        effect.succeed(999),
        effect.as_(42),
    )
    assert effect.run_sync(result) == 42  # noqa: PLR2004


def test_as_with_none() -> None:
    """Test that as_ can replace with None (common pattern)."""
    result = pipe(
        effect.succeed("some value"),
        effect.as_(None),
    )
    assert effect.run_sync(result) is None


def test_as_preserves_errors() -> None:
    """Test that as_ doesn't affect errors - they pass through unchanged."""
    eff = effect.fail(ValueError("oops"))
    replaced = effect.as_("new value")(eff)

    with pytest.raises(ValueError, match="oops"):
        effect.run_sync(replaced)


def test_as_preserves_errors_with_exit() -> None:
    """Test that as_ preserves errors when using run_sync_exit."""
    eff = effect.fail("error message")
    replaced = effect.as_("new value")(eff)
    result = effect.run_sync_exit(replaced)

    match result:
        case effect.Failure(error):
            assert error == "error message"
        case effect.Success(_):
            pytest.fail("Expected failure but got success")


async def test_as_with_async_effect() -> None:
    """Test that as_ works with async effects."""

    async def async_value() -> int:
        await asyncio.sleep(0.01)
        return 100

    eff = effect.async_(async_value)
    replaced = effect.as_("done")(eff)
    result = await effect.run_async(replaced)
    assert result == "done"


def test_as_with_sync_effect() -> None:
    """Test that as_ works with sync effects."""
    eff = effect.sync(lambda: 42)
    replaced = effect.as_("constant")(eff)
    result = effect.run_sync(replaced)
    assert result == "constant"


def test_as_composition() -> None:
    """Test composing multiple as_ operations (last one wins)."""
    result = pipe(
        effect.succeed(1),
        effect.as_(2),
        effect.as_(3),
        effect.as_(4),
    )
    assert effect.run_sync(result) == 4  # noqa: PLR2004


def test_as_after_map() -> None:
    """Test that as_ can replace a mapped value."""
    result = pipe(
        effect.succeed(10),
        effect.map(lambda x: x * 2),  # 20
        effect.as_("replaced"),  # Ignore the 20
    )
    assert effect.run_sync(result) == "replaced"


def test_map_after_as() -> None:
    """Test that map can transform an as_ value."""
    result = pipe(
        effect.succeed(999),
        effect.as_(10),  # Replace with 10
        effect.map(lambda x: x * 2),  # Transform the 10
    )
    assert effect.run_sync(result) == 20  # noqa: PLR2004


def test_as_with_type_change() -> None:
    """Test that as_ can change the type (int -> str -> bool)."""
    result = pipe(
        effect.succeed(42),
        effect.as_("string value"),
        effect.as_(True),
    )
    assert effect.run_sync(result) is True


def test_as_with_complex_value() -> None:
    """Test as_ with a complex value like a dict."""
    new_value = {"status": "success", "data": [1, 2, 3]}
    eff = effect.succeed("ignored")
    replaced = effect.as_(new_value)(eff)
    result = effect.run_sync(replaced)
    assert result == new_value


def test_as_is_lazy() -> None:
    """Test that as_ doesn't execute until the effect is run."""
    executed = []

    def track_execution() -> int:
        executed.append(1)
        return 42

    eff = effect.sync(track_execution)
    replaced = effect.as_("new value")(eff)

    # Effect is created but not executed
    assert len(executed) == 0

    # Now run it
    result = effect.run_sync(replaced)
    assert result == "new value"
    assert executed == [1]  # Original effect was executed


def test_as_with_tap() -> None:
    """Test that as_ works with tap."""
    tapped_values = []

    result = pipe(
        effect.succeed(10),
        effect.tap(lambda x: effect.sync(lambda: tapped_values.append(x))),
        effect.as_("replaced"),
    )

    final = effect.run_sync(result)
    assert final == "replaced"
    assert tapped_values == [10]  # Tap sees original value


def test_tap_after_as() -> None:
    """Test that tap sees the replaced value."""
    tapped_values = []

    result = pipe(
        effect.succeed(10),
        effect.as_(42),
        effect.tap(lambda x: effect.sync(lambda: tapped_values.append(x))),
    )

    final = effect.run_sync(result)
    assert final == 42  # noqa: PLR2004
    assert tapped_values == [42]  # Tap sees the replaced value


def test_as_with_try_sync() -> None:
    """Test that as_ works with try_sync effects."""
    eff = effect.try_sync(lambda: 21)
    replaced = effect.as_("success")(eff)
    result = effect.run_sync_exit(replaced)

    match result:
        case effect.Success(value):
            assert value == "success"
        case effect.Failure(_):
            pytest.fail("Expected success but got failure")


def test_as_with_try_sync_that_fails() -> None:
    """Test that as_ preserves exceptions from try_sync."""

    def will_fail() -> int:
        msg = "computation failed"
        raise ValueError(msg)

    eff = effect.try_sync(will_fail)
    replaced = effect.as_("new value")(eff)
    result = effect.run_sync_exit(replaced)

    match result:
        case effect.Failure(error):
            assert isinstance(error, ValueError)
            assert str(error) == "computation failed"
        case effect.Success(_):
            pytest.fail("Expected failure but got success")


async def test_as_with_try_async() -> None:
    """Test that as_ works with try_async effects."""

    async def async_computation() -> int:
        await asyncio.sleep(0.01)
        return 21

    eff = effect.try_async(async_computation)
    replaced = effect.as_("async success")(eff)
    result = await effect.run_async_exit(replaced)

    match result:
        case effect.Success(value):
            assert value == "async success"
        case effect.Failure(_):
            pytest.fail("Expected success but got failure")
