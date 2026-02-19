"""Tests for effect.catch_some."""

import pytest

from pyfect import effect, option, pipe

# ---------------------------------------------------------------------------
# Basic behaviour
# ---------------------------------------------------------------------------


def test_catch_some_some_recovers() -> None:
    eff = pipe(
        effect.fail("oops"),
        effect.catch_some(lambda _: option.some(effect.succeed("recovered"))),
    )
    assert effect.run_sync(eff) == "recovered"


def test_catch_some_nothing_propagates_error() -> None:
    eff = pipe(
        effect.fail("oops"),
        effect.catch_some(lambda _: option.nothing()),
    )
    result = effect.run_sync_exit(eff)
    assert isinstance(result, effect.Failure)
    assert result.error == "oops"


def test_catch_some_success_passes_through() -> None:
    called = False

    def handle(_: str) -> option.Option[effect.Effect[str]]:
        nonlocal called
        called = True
        return option.nothing()

    eff = pipe(effect.succeed("ok"), effect.catch_some(handle))
    assert effect.run_sync(eff) == "ok"
    assert not called


# ---------------------------------------------------------------------------
# Selective recovery — only some errors are handled
# ---------------------------------------------------------------------------


def test_catch_some_handles_only_matching_error() -> None:
    def handle(e: str) -> option.Option[effect.Effect[str]]:
        if e == "recoverable":
            return option.some(effect.succeed("recovered"))
        return option.nothing()

    eff_recovered = pipe(effect.fail("recoverable"), effect.catch_some(handle))
    assert effect.run_sync(eff_recovered) == "recovered"

    eff_unhandled = pipe(effect.fail("unrecoverable"), effect.catch_some(handle))
    result = effect.run_sync_exit(eff_unhandled)
    assert isinstance(result, effect.Failure)
    assert result.error == "unrecoverable"


def test_catch_some_isinstance_dispatch() -> None:
    """isinstance in the handler selects which error type to recover from."""

    class HttpError:
        pass

    class ValidationError:
        pass

    def handle(e: HttpError | ValidationError) -> option.Option[effect.Effect[str]]:
        if isinstance(e, HttpError):
            return option.some(effect.succeed("http recovered"))
        return option.nothing()

    eff_http = pipe(effect.fail(HttpError()), effect.catch_some(handle))
    assert effect.run_sync(eff_http) == "http recovered"

    eff_val = pipe(effect.fail(ValidationError()), effect.catch_some(handle))
    result = effect.run_sync_exit(eff_val)
    assert isinstance(result, effect.Failure)
    assert isinstance(result.error, ValidationError)


# ---------------------------------------------------------------------------
# Error type is preserved — the original E remains possible
# ---------------------------------------------------------------------------


def test_catch_some_error_type_preserved_on_nothing() -> None:
    """Nothing path re-fails with the original error value intact."""
    original = ValueError("original")
    eff = pipe(
        effect.fail(original),
        effect.catch_some(lambda _: option.nothing()),
    )
    result = effect.run_sync_exit(eff)
    assert isinstance(result, effect.Failure)
    assert result.error is original


# ---------------------------------------------------------------------------
# Recovery effect can itself fail
# ---------------------------------------------------------------------------


def test_catch_some_recovery_effect_can_fail() -> None:
    eff = pipe(
        effect.fail("first"),
        effect.catch_some(lambda _: option.some(effect.fail("second"))),
    )
    result = effect.run_sync_exit(eff)
    assert isinstance(result, effect.Failure)
    assert result.error == "second"


# ---------------------------------------------------------------------------
# Async
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_catch_some_async_some_recovers() -> None:
    eff = pipe(
        effect.fail("async oops"),
        effect.catch_some(lambda _: option.some(effect.succeed("async recovered"))),
    )
    assert await effect.run_async(eff) == "async recovered"


@pytest.mark.asyncio
async def test_catch_some_async_nothing_propagates() -> None:
    eff = pipe(
        effect.fail("async oops"),
        effect.catch_some(lambda _: option.nothing()),
    )
    result = await effect.run_async_exit(eff)
    assert isinstance(result, effect.Failure)
    assert result.error == "async oops"
