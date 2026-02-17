"""Tests for the effect.if_ combinator."""

import pytest

from pyfect import effect


def test_if_runs_on_true_branch() -> None:
    """When predicate is True, on_true is executed."""
    result = effect.if_(
        effect.succeed(True),
        on_true=effect.succeed("heads"),
        on_false=effect.succeed("tails"),
    )
    assert effect.run_sync(result) == "heads"


def test_if_runs_on_false_branch() -> None:
    """When predicate is False, on_false is executed."""
    result = effect.if_(
        effect.succeed(False),
        on_true=effect.succeed("heads"),
        on_false=effect.succeed("tails"),
    )
    assert effect.run_sync(result) == "tails"


def test_if_only_selected_branch_runs() -> None:
    """Only the effect for the selected branch is executed by the runtime."""
    executed: list[str] = []

    result = effect.if_(
        effect.succeed(True),
        on_true=effect.sync(lambda: executed.append("true") or "yes"),  # type: ignore[func-returns-value]
        on_false=effect.sync(lambda: executed.append("false") or "no"),  # type: ignore[func-returns-value]
    )

    effect.run_sync(result)
    assert executed == ["true"]


def test_if_false_branch_does_not_run_on_true() -> None:
    """on_false effect is not executed when predicate is True."""
    executed: list[str] = []

    effect.run_sync(
        effect.if_(
            effect.succeed(True),
            on_true=effect.sync(lambda: executed.append("true") or "yes"),  # type: ignore[func-returns-value]
            on_false=effect.sync(lambda: executed.append("false") or "no"),  # type: ignore[func-returns-value]
        )
    )
    assert "false" not in executed


def test_if_predicate_failure_propagates() -> None:
    """If the predicate fails, neither branch runs and the error propagates."""
    executed: list[str] = []

    with pytest.raises(ValueError, match="predicate error"):
        effect.run_sync(
            effect.if_(
                effect.fail(ValueError("predicate error")),
                on_true=effect.sync(lambda: executed.append("true") or "yes"),  # type: ignore[func-returns-value]
                on_false=effect.sync(lambda: executed.append("false") or "no"),  # type: ignore[func-returns-value]
            )
        )

    assert executed == []


def test_if_predicate_from_sync() -> None:
    """Predicate can be any boolean-producing effect."""
    result = effect.if_(
        effect.sync(lambda: 1 + 1 == 2),  # noqa: PLR2004
        on_true=effect.succeed(42),
        on_false=effect.succeed(0),
    )
    assert effect.run_sync(result) == 42  # noqa: PLR2004


def test_if_branches_can_have_different_success_types() -> None:
    """on_true and on_false may produce different types; result is their union."""
    result = effect.if_(
        effect.succeed(True),
        on_true=effect.succeed(42),
        on_false=effect.succeed("forty-two"),
    )
    value = effect.run_sync(result)
    assert value == 42  # noqa: PLR2004


def test_if_on_true_failure_propagates() -> None:
    """If on_true's effect fails, that error propagates."""
    result = effect.if_(
        effect.succeed(True),
        on_true=effect.fail(RuntimeError("branch error")),
        on_false=effect.succeed("nope"),
    )
    with pytest.raises(RuntimeError, match="branch error"):
        effect.run_sync(result)


def test_if_on_false_failure_propagates() -> None:
    """If on_false's effect fails, that error propagates."""
    result = effect.if_(
        effect.succeed(False),
        on_true=effect.succeed("nope"),
        on_false=effect.fail(RuntimeError("branch error")),
    )
    with pytest.raises(RuntimeError, match="branch error"):
        effect.run_sync(result)


def test_if_with_exit_true() -> None:
    """run_sync_exit works with if_ when predicate is True."""
    result = effect.if_(
        effect.succeed(True),
        on_true=effect.succeed("yes"),
        on_false=effect.succeed("no"),
    )
    match effect.run_sync_exit(result):
        case effect.Success(value):
            assert value == "yes"
        case effect.Failure(e):
            msg = f"Unexpected failure: {e}"
            raise AssertionError(msg)


def test_if_with_exit_predicate_failure() -> None:
    """run_sync_exit captures predicate failure as Exit.Failure."""
    result = effect.if_(
        effect.fail("predicate failed"),
        on_true=effect.succeed("yes"),
        on_false=effect.succeed("no"),
    )
    match effect.run_sync_exit(result):
        case effect.Failure(e):
            assert e == "predicate failed"
        case effect.Success(_):
            msg = "Expected failure"
            raise AssertionError(msg)


@pytest.mark.asyncio
async def test_if_async_true_branch() -> None:
    """if_ works with async execution on the true branch."""
    result = effect.if_(
        effect.succeed(True),
        on_true=effect.succeed("heads"),
        on_false=effect.succeed("tails"),
    )
    assert await effect.run_async(result) == "heads"


@pytest.mark.asyncio
async def test_if_async_false_branch() -> None:
    """if_ works with async execution on the false branch."""
    result = effect.if_(
        effect.succeed(False),
        on_true=effect.succeed("heads"),
        on_false=effect.succeed("tails"),
    )
    assert await effect.run_async(result) == "tails"
