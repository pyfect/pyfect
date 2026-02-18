"""Tests for the all_ combinator."""

import asyncio

import pytest

from pyfect import effect, either, option

# ============================================================================
# List — default mode
# ============================================================================


def test_all_list_default_all_succeed() -> None:
    """All effects succeed: returns list of values."""
    eff = effect.all_([effect.succeed(1), effect.succeed(2), effect.succeed(3)])
    assert effect.run_sync(eff) == [1, 2, 3]


def test_all_list_default_short_circuits_on_first_failure() -> None:
    """First failure short-circuits; subsequent effects are not run."""
    executed = []

    eff = effect.all_(
        [
            effect.succeed(1),
            effect.fail("boom"),
            effect.sync(lambda: executed.append(3) or 3),
        ]
    )

    result = effect.run_sync_exit(eff)
    match result:
        case effect.Failure(error):
            assert error == "boom"
        case effect.Success(_):
            pytest.fail("Expected failure")

    assert executed == [], "Effect after failure should not have run"


def test_all_list_default_empty() -> None:
    """Empty list succeeds with an empty list."""
    eff = effect.all_([])
    assert effect.run_sync(eff) == []


# ============================================================================
# List — either mode
# ============================================================================


def test_all_list_either_all_succeed() -> None:
    """Either mode wraps each success in Right, never short-circuits."""
    eff = effect.all_(
        [effect.succeed(1), effect.succeed(2)],
        mode="either",
    )
    result = effect.run_sync(eff)
    assert result == [either.Right(1), either.Right(2)]


def test_all_list_either_collects_all_failures() -> None:
    """Either mode collects both successes and failures without short-circuiting."""
    eff = effect.all_(
        [effect.succeed(1), effect.fail("err"), effect.succeed(3)],
        mode="either",
    )
    result = effect.run_sync(eff)
    assert result == [either.Right(1), either.Left("err"), either.Right(3)]


def test_all_list_either_all_fail() -> None:
    """Either mode with all failures returns all Lefts."""
    eff = effect.all_(
        [effect.fail("a"), effect.fail("b")],
        mode="either",
    )
    result = effect.run_sync(eff)
    assert result == [either.Left("a"), either.Left("b")]


def test_all_list_either_empty() -> None:
    """Either mode with empty list returns empty list."""
    eff = effect.all_([], mode="either")
    assert effect.run_sync(eff) == []


def test_all_list_either_accepts_allmode_enum() -> None:
    """AllMode.EITHER enum value works the same as the string literal."""
    eff = effect.all_(
        [effect.succeed(42)],
        mode=effect.AllMode.EITHER,
    )
    assert effect.run_sync(eff) == [either.Right(42)]


# ============================================================================
# List — validate mode
# ============================================================================


def test_all_list_validate_all_succeed() -> None:
    """Validate mode with all successes returns list of values."""
    eff = effect.all_(
        [effect.succeed(1), effect.succeed(2), effect.succeed(3)],
        mode="validate",
    )
    assert effect.run_sync(eff) == [1, 2, 3]


def test_all_list_validate_collects_all_errors() -> None:
    """Validate mode collects all errors as Some, successes as Nothing."""
    eff = effect.all_(
        [effect.succeed(1), effect.fail("err1"), effect.succeed(3), effect.fail("err2")],
        mode="validate",
    )
    result = effect.run_sync_exit(eff)
    match result:
        case effect.Failure(errors):
            assert errors == [
                option.nothing(),
                option.some("err1"),
                option.nothing(),
                option.some("err2"),
            ]
        case effect.Success(_):
            pytest.fail("Expected failure")


def test_all_list_validate_empty() -> None:
    """Validate mode with empty list succeeds with empty list."""
    eff = effect.all_([], mode="validate")
    assert effect.run_sync(eff) == []


def test_all_list_validate_accepts_allmode_enum() -> None:
    """AllMode.VALIDATE enum value works the same as the string literal."""
    eff = effect.all_(
        [effect.succeed(1), effect.fail("oops")],
        mode=effect.AllMode.VALIDATE,
    )
    result = effect.run_sync_exit(eff)
    match result:
        case effect.Failure(errors):
            assert errors == [option.nothing(), option.some("oops")]
        case effect.Success(_):
            pytest.fail("Expected failure")


# ============================================================================
# Dict — default mode
# ============================================================================


def test_all_dict_default_all_succeed() -> None:
    """Dict default mode returns dict of values keyed by original keys."""
    eff = effect.all_(
        {
            "a": effect.succeed(1),
            "b": effect.succeed(2),
            "c": effect.succeed(3),
        }
    )
    assert effect.run_sync(eff) == {"a": 1, "b": 2, "c": 3}


def test_all_dict_default_short_circuits_on_failure() -> None:
    """Dict default mode short-circuits on first failure."""
    eff = effect.all_(
        {
            "a": effect.succeed(1),
            "b": effect.fail("boom"),
            "c": effect.succeed(3),
        }
    )
    result = effect.run_sync_exit(eff)
    match result:
        case effect.Failure(error):
            assert error == "boom"
        case effect.Success(_):
            pytest.fail("Expected failure")


def test_all_dict_default_empty() -> None:
    """Empty dict succeeds with an empty dict."""
    eff: effect.Effect[dict[str, int], str] = effect.all_({})
    assert effect.run_sync(eff) == {}


def test_all_dict_default_accepts_allmode_enum() -> None:
    """AllMode.DEFAULT enum value works the same as the default."""
    eff = effect.all_(
        {"x": effect.succeed(10)},
        mode=effect.AllMode.DEFAULT,
    )
    assert effect.run_sync(eff) == {"x": 10}


# ============================================================================
# Dict — either mode
# ============================================================================


def test_all_dict_either_all_succeed() -> None:
    """Dict either mode wraps each success in Right."""
    eff = effect.all_(
        {"a": effect.succeed(1), "b": effect.succeed(2)},
        mode="either",
    )
    result = effect.run_sync(eff)
    assert result == {"a": either.Right(1), "b": either.Right(2)}


def test_all_dict_either_collects_all_failures() -> None:
    """Dict either mode collects both Rights and Lefts without short-circuiting."""
    eff = effect.all_(
        {"a": effect.succeed(1), "b": effect.fail("err"), "c": effect.succeed(3)},
        mode="either",
    )
    result = effect.run_sync(eff)
    assert result == {
        "a": either.Right(1),
        "b": either.Left("err"),
        "c": either.Right(3),
    }


# ============================================================================
# Dict — validate mode
# ============================================================================


def test_all_dict_validate_all_succeed() -> None:
    """Dict validate mode with all successes returns dict of values."""
    eff = effect.all_(
        {"a": effect.succeed(1), "b": effect.succeed(2)},
        mode="validate",
    )
    assert effect.run_sync(eff) == {"a": 1, "b": 2}


def test_all_dict_validate_collects_all_errors() -> None:
    """Dict validate mode collects all errors keyed by their keys."""
    eff = effect.all_(
        {"a": effect.succeed(1), "b": effect.fail("err"), "c": effect.succeed(3)},
        mode="validate",
    )
    result = effect.run_sync_exit(eff)
    match result:
        case effect.Failure(errors):
            assert errors == {
                "a": option.nothing(),
                "b": option.some("err"),
                "c": option.nothing(),
            }
        case effect.Success(_):
            pytest.fail("Expected failure")


def test_all_dict_validate_all_fail() -> None:
    """Dict validate mode with all failures returns all Somes in error dict."""
    eff = effect.all_(
        {"a": effect.fail("err_a"), "b": effect.fail("err_b")},
        mode="validate",
    )
    result = effect.run_sync_exit(eff)
    match result:
        case effect.Failure(errors):
            assert errors == {"a": option.some("err_a"), "b": option.some("err_b")}
        case effect.Success(_):
            pytest.fail("Expected failure")


# ============================================================================
# Concurrent execution
# ============================================================================


async def test_all_list_default_concurrent() -> None:
    """Concurrent list default mode runs effects in parallel."""
    order: list[int] = []

    async def slow(n: int, delay: float) -> int:
        await asyncio.sleep(delay)
        order.append(n)
        return n

    eff = effect.all_(
        [
            effect.async_(lambda: slow(1, 0.05)),
            effect.async_(lambda: slow(2, 0.01)),
            effect.async_(lambda: slow(3, 0.03)),
        ],
        concurrent=True,
    )
    result = await effect.run_async(eff)
    assert result == [1, 2, 3]
    # Concurrent: completes in order of delay (2, 3, 1) not input order
    assert order == [2, 3, 1]


async def test_all_dict_default_concurrent() -> None:
    """Concurrent dict default mode runs effects in parallel and keys results correctly."""
    order: list[str] = []

    async def slow(key: str, delay: float) -> str:
        await asyncio.sleep(delay)
        order.append(key)
        return key.upper()

    eff = effect.all_(
        {
            "a": effect.async_(lambda: slow("a", 0.05)),
            "b": effect.async_(lambda: slow("b", 0.01)),
            "c": effect.async_(lambda: slow("c", 0.03)),
        },
        concurrent=True,
    )
    result = await effect.run_async(eff)
    assert result == {"a": "A", "b": "B", "c": "C"}
    # Concurrent: completes in order of delay (b, c, a) not insertion order
    assert order == ["b", "c", "a"]


async def test_all_list_either_async() -> None:
    """Either mode works through the async runtime (covers async Absorb path)."""

    async def ok() -> int:
        await asyncio.sleep(0)
        return 42

    eff = effect.all_(
        [effect.async_(ok), effect.fail("err"), effect.async_(ok)],
        mode="either",
    )
    result = await effect.run_async(eff)
    assert result == [either.Right(42), either.Left("err"), either.Right(42)]


async def test_all_list_validate_async() -> None:
    """Validate mode works through the async runtime (covers async Absorb path)."""

    async def ok() -> int:
        await asyncio.sleep(0)
        return 1

    eff = effect.all_(
        [effect.async_(ok), effect.fail("oops")],
        mode="validate",
    )
    result = await effect.run_async_exit(eff)
    match result:
        case effect.Failure(errors):
            assert errors == [option.nothing(), option.some("oops")]
        case effect.Success(_):
            pytest.fail("Expected failure")


# ============================================================================
# Heterogeneous collections
# ============================================================================


def test_all_list_heterogeneous_default() -> None:
    """Heterogeneous list (mixed value types) collects into a list[int | str]."""
    eff = effect.all_(
        [
            effect.succeed(1),
            effect.succeed("hello"),
            effect.succeed(3),
        ]
    )
    result = effect.run_sync(eff)
    assert result == [1, "hello", 3]


def test_all_list_heterogeneous_either() -> None:
    """Heterogeneous list in either mode wraps each value in Right."""
    eff = effect.all_(
        [
            effect.succeed(1),
            effect.fail("oops"),
            effect.succeed("hello"),
        ],
        mode="either",
    )
    result = effect.run_sync(eff)
    assert result == [either.Right(1), either.Left("oops"), either.Right("hello")]


def test_all_dict_heterogeneous_default() -> None:
    """Heterogeneous dict (mixed value types) collects into a dict[str, int | str]."""
    eff = effect.all_(
        {
            "count": effect.succeed(42),
            "label": effect.succeed("hello"),
        }
    )
    result = effect.run_sync(eff)
    assert result == {"count": 42, "label": "hello"}


def test_all_dict_heterogeneous_validate() -> None:
    """Heterogeneous dict in validate mode reports errors per key."""
    eff = effect.all_(
        {
            "count": effect.succeed(42),
            "label": effect.fail("missing"),
        },
        mode="validate",
    )
    result = effect.run_sync_exit(eff)
    match result:
        case effect.Failure(errors):
            assert errors == {"count": option.nothing(), "label": option.some("missing")}
        case effect.Success(_):
            pytest.fail("Expected failure")
