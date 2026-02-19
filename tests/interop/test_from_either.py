"""Tests for effect.from_either."""

import pytest

from pyfect import effect, either


def test_from_either_right_succeeds() -> None:
    eff = effect.from_either(either.right(42))
    result = effect.run_sync(eff)
    assert result == 42  # noqa: PLR2004


def test_from_either_left_fails() -> None:
    eff = effect.from_either(either.left("oops"))
    result = effect.run_sync_exit(eff)
    assert isinstance(result, effect.Failure)
    assert result.error == "oops"


def test_from_either_right_raises_on_run_sync_exit() -> None:
    eff = effect.from_either(either.right(42))
    result = effect.run_sync_exit(eff)
    assert isinstance(result, effect.Success)
    assert result.value == 42  # noqa: PLR2004


def test_from_either_left_raises_on_run_sync() -> None:
    eff = effect.from_either(either.left("oops"))
    with pytest.raises(Exception, match="oops"):
        effect.run_sync(eff)
