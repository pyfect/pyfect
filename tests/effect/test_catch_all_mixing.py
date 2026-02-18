"""Tests for catch_all mixing types, combinators, and chaining."""

from dataclasses import dataclass

import pytest

from pyfect import effect, either, option, pipe

# ---------------------------------------------------------------------------
# Domain error types used throughout
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HttpError:
    status: int


@dataclass(frozen=True)
class ValidationError:
    field: str


# ---------------------------------------------------------------------------
# Union error types
# ---------------------------------------------------------------------------


def test_catch_all_union_error_success_branch() -> None:
    """A program with a union error type that succeeds — handler never called."""

    def program(fail: bool) -> effect.Effect[str, HttpError | ValidationError]:
        if fail:
            return effect.fail(HttpError(500))
        return effect.succeed("ok")

    result = effect.run_sync(
        pipe(program(False), effect.catch_all(lambda _: effect.succeed("fallback")))
    )
    assert result == "ok"


def test_catch_all_union_error_http_branch() -> None:
    program: effect.Effect[str, HttpError | ValidationError] = effect.fail(HttpError(404))
    result = effect.run_sync(
        pipe(
            program,
            effect.catch_all(lambda e: effect.succeed(f"http:{e.status}")),  # type: ignore[union-attr]
        )
    )
    assert result == "http:404"


def test_catch_all_union_error_dispatch_by_type() -> None:
    """Handler inspects the error type at runtime to branch recovery."""

    def recover(e: HttpError | ValidationError) -> effect.Effect[str]:
        if isinstance(e, HttpError):
            return effect.succeed(f"http {e.status}")
        return effect.succeed(f"validation: {e.field}")

    http_result = effect.run_sync(pipe(effect.fail(HttpError(503)), effect.catch_all(recover)))
    val_result = effect.run_sync(
        pipe(effect.fail(ValidationError("email")), effect.catch_all(recover))
    )

    assert http_result == "http 503"
    assert val_result == "validation: email"


# ---------------------------------------------------------------------------
# Success type widening (A | A2)
# ---------------------------------------------------------------------------


def test_catch_all_widens_success_type() -> None:
    """On failure the fallback returns a different type; the union is the result."""
    # program: Effect[int, str]   fallback: Effect[str, Never]
    # result:  Effect[int | str, Never]  # noqa: ERA001
    result_ok = effect.run_sync(
        pipe(effect.succeed(42), effect.catch_all(lambda _: effect.succeed("default")))
    )
    result_err = effect.run_sync(
        pipe(effect.fail("gone"), effect.catch_all(lambda _: effect.succeed("default")))
    )
    assert result_ok == 42  # noqa: PLR2004
    assert result_err == "default"


# ---------------------------------------------------------------------------
# Chaining with map_ and flat_map
# ---------------------------------------------------------------------------


def test_catch_all_after_flat_map_failure() -> None:
    """flat_map introduces a new error; catch_all handles it."""

    def risky(n: int) -> effect.Effect[int, str]:
        if n < 0:
            return effect.fail("negative")
        return effect.succeed(n * 2)

    result = effect.run_sync(
        pipe(
            effect.succeed(-1),
            effect.flat_map(risky),
            effect.catch_all(lambda _: effect.succeed(-999)),
        )
    )
    assert result == -999  # noqa: PLR2004


def test_catch_all_followed_by_map() -> None:
    """map_ transforms the recovered value just like any success value."""
    result = effect.run_sync(
        pipe(
            effect.fail("error"),
            effect.catch_all(lambda _: effect.succeed(0)),
            effect.map_(lambda n: n + 100),
        )
    )
    assert result == 100  # noqa: PLR2004


def test_map_error_then_catch_all() -> None:
    """map_error reshapes the error; catch_all then handles the new shape."""
    result = effect.run_sync(
        pipe(
            effect.fail(404),
            effect.map_error(HttpError),
            effect.catch_all(lambda e: effect.succeed(f"status={e.status}")),
        )
    )
    assert result == "status=404"


# ---------------------------------------------------------------------------
# Combining with either / option
# ---------------------------------------------------------------------------


def test_catch_all_then_either_is_always_right() -> None:
    """After catch_all with an infallible fallback, either always gives Right."""
    eff = pipe(
        effect.fail("bad"),
        effect.catch_all(lambda _: effect.succeed("recovered")),
        effect.either,
    )
    result = effect.run_sync(eff)
    assert isinstance(result, either.Right)
    assert result.value == "recovered"


def test_either_then_catch_all() -> None:
    """effect.either surfaces errors as values; catch_all never fires."""
    caught = False

    def handle(_: object) -> effect.Effect[str]:
        nonlocal caught
        caught = True
        return effect.succeed("fallback")

    result = effect.run_sync(
        pipe(
            effect.fail("inner"),
            effect.either,  # absorbs the failure
            effect.catch_all(handle),  # never invoked
        )
    )
    assert not caught
    assert isinstance(result, either.Left)
    assert result.value == "inner"


def test_catch_all_then_option_on_success() -> None:
    result = effect.run_sync(
        pipe(
            effect.fail("x"),
            effect.catch_all(lambda _: effect.succeed(7)),
            effect.option,
        )
    )
    assert isinstance(result, option.Some)
    assert result.value == 7  # noqa: PLR2004


# ---------------------------------------------------------------------------
# Chaining two catch_all calls
# ---------------------------------------------------------------------------


def test_catch_all_chain_first_handles() -> None:
    """When the first catch_all succeeds, the second is not triggered."""
    calls: list[str] = []

    def first(_: str) -> effect.Effect[str, int]:
        calls.append("first")
        return effect.succeed("from first")

    def second(_: int) -> effect.Effect[str, None]:
        calls.append("second")
        return effect.succeed("from second")

    result = effect.run_sync(
        pipe(effect.fail("initial"), effect.catch_all(first), effect.catch_all(second))
    )
    assert result == "from first"
    assert calls == ["first"]


def test_catch_all_chain_first_re_raises() -> None:
    """First catch_all returns a new failure; second handles it."""

    def first(e: str) -> effect.Effect[str, int]:
        return effect.fail(len(e))

    def second(n: int) -> effect.Effect[str, None]:
        return effect.succeed(f"length was {n}")

    result = effect.run_sync(
        pipe(effect.fail("hello"), effect.catch_all(first), effect.catch_all(second))
    )
    assert result == "length was 5"


# ---------------------------------------------------------------------------
# Async mixing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_catch_all_async_with_map() -> None:
    result = await effect.run_async(
        pipe(
            effect.fail(HttpError(500)),
            effect.catch_all(lambda e: effect.succeed(e.status)),
            effect.map_(lambda code: code * 2),
        )
    )
    assert result == 1000  # noqa: PLR2004


@pytest.mark.asyncio
async def test_catch_all_async_union_dispatch() -> None:
    def recover(e: HttpError | ValidationError) -> effect.Effect[str, None]:
        if isinstance(e, HttpError):
            return effect.succeed(f"http:{e.status}")
        return effect.succeed(f"field:{e.field}")

    r1 = await effect.run_async(pipe(effect.fail(HttpError(404)), effect.catch_all(recover)))
    r2 = await effect.run_async(
        pipe(effect.fail(ValidationError("name")), effect.catch_all(recover))
    )
    assert r1 == "http:404"
    assert r2 == "field:name"
