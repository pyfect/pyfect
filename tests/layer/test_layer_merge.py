"""Tests for layer.merge."""

import pytest

from pyfect import effect, layer, pipe


class Config:
    def __init__(self, level: str) -> None:
        self.level = level


class Logger:
    def __init__(self, name: str) -> None:
        self.name = name


class Cache:
    def __init__(self, size: int) -> None:
        self.size = size


def test_merge_two_succeed_layers() -> None:
    """Merged layer satisfies an effect requiring both services."""
    config = Config("INFO")
    logger = Logger("app")

    app_layer = layer.merge(
        layer.succeed(Config, config),
        layer.succeed(Logger, logger),
    )

    eff = pipe(
        effect.service(Config, Logger),
        effect.provide(app_layer),
    )

    c, l = effect.run_sync(eff)  # noqa: E741
    assert c is config
    assert l is logger


def test_merge_three_layers() -> None:
    """Merging can be chained for more than two services."""
    config = Config("INFO")
    logger = Logger("app")
    cache = Cache(256)

    app_layer = layer.merge(
        layer.merge(
            layer.succeed(Config, config),
            layer.succeed(Logger, logger),
        ),
        layer.succeed(Cache, cache),
    )

    eff = pipe(
        effect.service(Config, Logger, Cache),
        effect.provide(app_layer),
    )

    c, l, ca = effect.run_sync(eff)  # noqa: E741
    assert c is config
    assert l is logger
    assert ca is cache


def test_merge_right_wins_on_collision() -> None:
    """When both layers produce the same service, the right layer's value is used."""
    config1 = Config("INFO")
    config2 = Config("DEBUG")

    merged = layer.merge(
        layer.succeed(Config, config1),
        layer.succeed(Config, config2),
    )

    eff = pipe(
        effect.service(Config),
        effect.provide(merged),
    )

    result = effect.run_sync(eff)
    assert result is config2


def test_merge_propagates_left_construction_failure() -> None:
    """If the left layer's construction fails, the merged layer fails."""

    class BuildError(Exception):
        pass

    merged = layer.merge(
        layer.effect(Config, effect.fail(BuildError("left failed"))),
        layer.succeed(Logger, Logger("app")),
    )

    eff = pipe(
        effect.service(Config, Logger),
        effect.provide(merged),
    )

    with pytest.raises(BuildError, match="left failed"):
        effect.run_sync(eff)


@pytest.mark.asyncio
async def test_merge_async() -> None:
    """Merged layer works with async execution."""
    config = Config("INFO")
    logger = Logger("app")

    app_layer = layer.merge(
        layer.succeed(Config, config),
        layer.succeed(Logger, logger),
    )

    eff = pipe(
        effect.service(Config, Logger),
        effect.provide(app_layer),
    )

    c, l = await effect.run_async(eff)  # noqa: E741
    assert c is config
    assert l is logger
