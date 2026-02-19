"""Tests for effect.catch_if."""

from typing import TypeGuard

import pytest

from pyfect import effect, pipe

# ---------------------------------------------------------------------------
# Basic behaviour
# ---------------------------------------------------------------------------


def test_catch_if_predicate_true_recovers() -> None:
    eff = pipe(
        effect.fail("oops"),
        effect.catch_if(lambda _: True, lambda _: effect.succeed("recovered")),
    )
    assert effect.run_sync(eff) == "recovered"


def test_catch_if_predicate_false_propagates_error() -> None:
    eff = pipe(
        effect.fail("oops"),
        effect.catch_if(lambda _: False, lambda _: effect.succeed("recovered")),
    )
    result = effect.run_sync_exit(eff)
    assert isinstance(result, effect.Failure)
    assert result.error == "oops"


def test_catch_if_success_passes_through() -> None:
    called = False

    def predicate(_: str) -> bool:
        nonlocal called
        called = True
        return True

    eff = pipe(effect.succeed("ok"), effect.catch_if(predicate, lambda _: effect.succeed("x")))
    assert effect.run_sync(eff) == "ok"
    assert not called


# ---------------------------------------------------------------------------
# Selective recovery — predicate inspects the error value
# ---------------------------------------------------------------------------


def test_catch_if_handles_only_matching_error() -> None:
    eff_recovered = pipe(
        effect.fail("recoverable"),
        effect.catch_if(lambda e: e == "recoverable", lambda _: effect.succeed("recovered")),
    )
    assert effect.run_sync(eff_recovered) == "recovered"

    eff_unhandled = pipe(
        effect.fail("unrecoverable"),
        effect.catch_if(lambda e: e == "recoverable", lambda _: effect.succeed("recovered")),
    )
    result = effect.run_sync_exit(eff_unhandled)
    assert isinstance(result, effect.Failure)
    assert result.error == "unrecoverable"


def test_catch_if_isinstance_predicate() -> None:
    class HttpError:
        pass

    class ValidationError:
        pass

    eff_http = pipe(
        effect.fail(HttpError()),
        effect.catch_if(
            lambda e: isinstance(e, HttpError),
            lambda _: effect.succeed("http recovered"),
        ),
    )
    assert effect.run_sync(eff_http) == "http recovered"

    def create_error(x: int) -> HttpError | ValidationError:
        return HttpError() if x % 2 == 0 else ValidationError()

    eff_val = pipe(
        effect.fail(create_error(1)),
        effect.catch_if(
            lambda e: isinstance(e, HttpError),
            lambda _: effect.succeed("http recovered"),
        ),
    )
    result = effect.run_sync_exit(eff_val)
    assert isinstance(result, effect.Failure)
    assert isinstance(result.error, ValidationError)


# ---------------------------------------------------------------------------
# TypeGuard overload — recover receives the narrowed type
# ---------------------------------------------------------------------------


def test_catch_if_typeguard_predicate() -> None:
    class HttpError:
        def __init__(self, code: int) -> None:
            self.code = code

    class ValidationError:
        pass

    def create_error(x: int) -> HttpError | ValidationError:
        return HttpError(404) if x % 2 == 0 else ValidationError()

    def is_http(e: HttpError | ValidationError) -> TypeGuard[HttpError]:
        return isinstance(e, HttpError)

    eff = pipe(
        effect.fail(create_error(0)),
        effect.catch_if(is_http, lambda e: effect.succeed(f"code={e.code}")),
    )
    assert effect.run_sync(eff) == "code=404"


# ---------------------------------------------------------------------------
# Error value is preserved on non-match
# ---------------------------------------------------------------------------


def test_catch_if_original_error_value_preserved() -> None:
    original = ValueError("original")
    eff = pipe(
        effect.fail(original),
        effect.catch_if(lambda _: False, lambda _: effect.succeed("x")),
    )
    result = effect.run_sync_exit(eff)
    assert isinstance(result, effect.Failure)
    assert result.error is original


# ---------------------------------------------------------------------------
# Recovery effect can itself fail
# ---------------------------------------------------------------------------


def test_catch_if_recovery_effect_can_fail() -> None:
    eff = pipe(
        effect.fail("first"),
        effect.catch_if(lambda _: True, lambda _: effect.fail("second")),
    )
    result = effect.run_sync_exit(eff)
    assert isinstance(result, effect.Failure)
    assert result.error == "second"


# ---------------------------------------------------------------------------
# Async
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_catch_if_async_predicate_true_recovers() -> None:
    eff = pipe(
        effect.fail("async oops"),
        effect.catch_if(lambda _: True, lambda _: effect.succeed("async recovered")),
    )
    assert await effect.run_async(eff) == "async recovered"


@pytest.mark.asyncio
async def test_catch_if_async_predicate_false_propagates() -> None:
    eff = pipe(
        effect.fail("async oops"),
        effect.catch_if(lambda _: False, lambda _: effect.succeed("x")),
    )
    result = await effect.run_async_exit(eff)
    assert isinstance(result, effect.Failure)
    assert result.error == "async oops"
