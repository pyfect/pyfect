"""Tests for layer.effect."""

import pytest

from pyfect import effect, layer, pipe


class Logger:
    def __init__(self, level: str) -> None:
        self.level = level


def test_effect_with_plain_succeed() -> None:
    """layer.effect wrapping a plain succeed behaves like layer.succeed."""
    logger_layer = layer.effect(Logger, effect.succeed(Logger("INFO")))

    eff = pipe(
        effect.service(Logger),
        effect.provide(logger_layer),
    )

    result = effect.run_sync(eff)
    assert isinstance(result, Logger)
    assert result.level == "INFO"


def test_effect_propagates_construction_failure() -> None:
    """If the construction effect fails, provide propagates the error."""

    class BuildError(Exception):
        pass

    failing_layer = layer.effect(Logger, effect.fail(BuildError("build failed")))

    eff = pipe(
        effect.service(Logger),
        effect.provide(failing_layer),
    )

    with pytest.raises(BuildError, match="build failed"):
        effect.run_sync(eff)


@pytest.mark.asyncio
async def test_effect_with_async_construction() -> None:
    """layer.effect works with async effects."""

    async def build_logger() -> Logger:
        return Logger("ASYNC")

    logger_layer = layer.effect(Logger, effect.async_(build_logger))

    eff = pipe(
        effect.service(Logger),
        effect.provide(logger_layer),
    )

    result = await effect.run_async(eff)
    assert result.level == "ASYNC"
