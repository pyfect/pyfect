"""Tests for layer.provide."""

import pytest

from pyfect import effect, layer, pipe


class Config:
    def __init__(self, level: str) -> None:
        self.level = level


class Logger:
    def __init__(self, level: str) -> None:
        self.level = level


class Database:
    def __init__(self, url: str) -> None:
        self.url = url


def test_provide_satisfies_single_dependency() -> None:
    """provide wires an outer layer into an inner layer's requirement."""
    config = Config("INFO")

    logger_layer = layer.effect(
        Logger,
        pipe(effect.service(Config), effect.map(lambda c: Logger(c.level))),
    )

    config_layer = layer.succeed(Config, config)

    app_layer = pipe(
        logger_layer,
        layer.provide(config_layer),
    )

    eff = pipe(
        effect.service(Logger),
        effect.provide(app_layer),
    )

    logger = effect.run_sync(eff)
    assert logger.level == "INFO"


def test_provide_chains_two_dependencies() -> None:
    """provide can be chained to resolve transitive dependencies."""
    config = Config("DEBUG")

    logger_layer = layer.effect(
        Logger,
        pipe(effect.service(Config), effect.map(lambda c: Logger(c.level))),
    )

    database_layer = layer.effect(
        Database,
        pipe(
            effect.service(Logger),
            effect.map(lambda l: Database(f"postgres://{l.level}")),  # noqa: E741
        ),
    )

    config_layer = layer.succeed(Config, config)

    app_layer = pipe(
        database_layer,
        layer.provide(logger_layer),
        layer.provide(config_layer),
    )

    eff = pipe(
        effect.service(Database),
        effect.provide(app_layer),
    )

    db = effect.run_sync(eff)
    assert db.url == "postgres://DEBUG"


def test_provide_propagates_construction_failure() -> None:
    """If the outer layer fails during construction, provide propagates the error."""

    class BuildError(Exception):
        pass

    logger_layer = layer.effect(
        Logger,
        pipe(effect.service(Config), effect.map(lambda c: Logger(c.level))),
    )

    failing_config_layer = layer.effect(Config, effect.fail(BuildError("no config")))

    app_layer = pipe(
        logger_layer,
        layer.provide(failing_config_layer),
    )

    eff = pipe(
        effect.service(Logger),
        effect.provide(app_layer),
    )

    with pytest.raises(BuildError, match="no config"):
        effect.run_sync(eff)


def test_provide_with_merged_outer_layer() -> None:
    """provide works when the outer layer is a merge of multiple layers."""
    config = Config("INFO")
    logger = Logger("app")

    database_layer = layer.effect(
        Database,
        pipe(
            effect.service(Config, Logger),
            effect.map(lambda c_l: Database(f"{c_l[0].level}-{c_l[1].level}")),
        ),
    )

    app_layer = pipe(
        database_layer,
        layer.provide(layer.merge(layer.succeed(Config, config), layer.succeed(Logger, logger))),
    )

    eff = pipe(
        effect.service(Database),
        effect.provide(app_layer),
    )

    db = effect.run_sync(eff)
    assert db.url == "INFO-app"


@pytest.mark.asyncio
async def test_provide_async() -> None:
    """provide works with async execution."""
    config = Config("INFO")

    logger_layer = layer.effect(
        Logger,
        pipe(effect.service(Config), effect.map(lambda c: Logger(c.level))),
    )

    app_layer = pipe(
        logger_layer,
        layer.provide(layer.succeed(Config, config)),
    )

    eff = pipe(
        effect.service(Logger),
        effect.provide(app_layer),
    )

    logger = await effect.run_async(eff)
    assert logger.level == "INFO"
