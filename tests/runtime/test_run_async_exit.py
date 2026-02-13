"""Tests for run_async_exit missing coverage branches."""

from pyfect import effect


async def test_tap_on_failure_returns_failure() -> None:
    eff = effect.tap(lambda _: effect.succeed(None))(effect.fail("oops"))
    result = await effect.run_async_exit(eff)
    assert isinstance(result, effect.Failure)
    assert result.error == "oops"


async def test_flat_map_on_failure_returns_failure() -> None:
    eff = effect.flat_map(lambda _: effect.succeed(1))(effect.fail("oops"))
    result = await effect.run_async_exit(eff)
    assert isinstance(result, effect.Failure)
    assert result.error == "oops"


async def test_map_error_on_success_returns_success() -> None:
    eff = effect.map_error(lambda e: f"transformed: {e}")(effect.succeed(42))
    result = await effect.run_async_exit(eff)
    assert isinstance(result, effect.Success)
    assert result.value == 42  # noqa: PLR2004


async def test_tap_error_on_success_returns_success() -> None:
    side_effects: list[str] = []
    eff = effect.tap_error(lambda e: effect.sync(lambda: side_effects.append(str(e))))(
        effect.succeed(42)
    )
    result = await effect.run_async_exit(eff)
    assert isinstance(result, effect.Success)
    assert result.value == 42  # noqa: PLR2004
    assert side_effects == []


async def test_tap_error_on_failure_runs_side_effect_and_returns_failure() -> None:
    side_effects: list[str] = []
    eff = effect.tap_error(lambda e: effect.sync(lambda: side_effects.append(str(e))))(
        effect.fail("oops")
    )
    result = await effect.run_async_exit(eff)
    assert isinstance(result, effect.Failure)
    assert result.error == "oops"
    assert side_effects == ["oops"]


async def test_try_sync_failure_returns_failure() -> None:
    result = await effect.run_async_exit(effect.try_sync(lambda: int("not a number")))
    assert isinstance(result, effect.Failure)
    assert isinstance(result.error, ValueError)
