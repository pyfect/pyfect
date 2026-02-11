"""Tests for effect.from_either."""

import pytest

from pyfect import effect, either


def test_from_either_right_succeeds() -> None:
    result = effect.run_sync(effect.from_either(either.right(42)))
    assert result == 42  # noqa: PLR2004


def test_from_either_left_fails() -> None:
    result = effect.run_sync_exit(effect.from_either(either.left("oops")))
    assert isinstance(result, effect.Failure)
    assert result.error == "oops"


def test_from_either_right_raises_on_run_sync_exit() -> None:
    result = effect.run_sync_exit(effect.from_either(either.right(42)))
    assert isinstance(result, effect.Success)
    assert result.value == 42  # noqa: PLR2004


def test_from_either_left_raises_on_run_sync() -> None:
    with pytest.raises(Exception, match="oops"):
        effect.run_sync(effect.from_either(either.left("oops")))
