"""Tests for effect.die."""

import pytest

from pyfect import effect


def test_die_raises_with_run_sync() -> None:
    eff = effect.die(ValueError("boom"))
    with pytest.raises(ValueError, match="boom"):
        effect.run_sync(eff)


def test_die_bypasses_exit() -> None:
    """die is a defect — it raises even with run_sync_exit."""
    eff = effect.die(ValueError("boom"))
    with pytest.raises(ValueError, match="boom"):
        effect.run_sync_exit(eff)


def test_die_type_inference() -> None:
    """Hover over eff — should show Effect[Never, Never, Never]."""
    eff = effect.die(RuntimeError("defect"))
    with pytest.raises(RuntimeError):
        effect.run_sync(eff)


@pytest.mark.asyncio
async def test_die_raises_with_run_async() -> None:
    eff = effect.die(ValueError("async boom"))
    with pytest.raises(ValueError, match="async boom"):
        await effect.run_async(eff)
