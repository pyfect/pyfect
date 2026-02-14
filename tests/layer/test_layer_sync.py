"""Tests for layer.sync."""

import pytest

from pyfect import effect, layer, pipe


class Logger:
    def __init__(self, level: str) -> None:
        self.level = level


class Counter:
    def __init__(self) -> None:
        self.count = 0


def test_sync_provides_service() -> None:
    """A layer.sync layer can be provided to a sync effect."""
    logger_layer = layer.sync(Logger, lambda: Logger("INFO"))

    eff = pipe(
        effect.service(Logger),
        effect.provide(logger_layer),
    )

    result = effect.run_sync(eff)
    assert isinstance(result, Logger)
    assert result.level == "INFO"


@pytest.mark.asyncio
async def test_sync_provides_service_async() -> None:
    """A layer.sync layer can be provided to an async effect."""
    logger_layer = layer.sync(Logger, lambda: Logger("DEBUG"))

    eff = pipe(
        effect.service(Logger),
        effect.provide(logger_layer),
    )

    result = await effect.run_async(eff)
    assert result.level == "DEBUG"


def test_sync_thunk_called_at_provision_time() -> None:
    """The thunk is called when the layer is provided, not when it is defined."""
    calls: list[int] = []

    def build_logger() -> Logger:
        calls.append(1)
        return Logger("INFO")

    logger_layer = layer.sync(Logger, build_logger)
    assert calls == []

    eff = pipe(effect.service(Logger), effect.provide(logger_layer))
    effect.run_sync(eff)
    assert calls == [1]


def test_sync_thunk_called_on_each_run() -> None:
    """Each run calls the thunk again, producing a fresh instance."""
    logger_layer = layer.sync(Logger, lambda: Logger("INFO"))

    eff = pipe(effect.service(Logger), effect.provide(logger_layer))

    result1 = effect.run_sync(eff)
    result2 = effect.run_sync(eff)
    assert result1 is not result2
