"""Tests for layer.succeed and effect.provide with a Layer."""

import pytest

from pyfect import context, effect, layer, pipe


class Config:
    def __init__(self, level: str) -> None:
        self.level = level


class Database:
    def __init__(self, url: str) -> None:
        self.url = url


class Logger:
    def __init__(self, name: str) -> None:
        self.name = name


def test_succeed_provides_service_sync() -> None:
    """A layer.succeed layer can be provided to a sync effect."""
    config = Config("INFO")
    config_layer = layer.succeed(Config, config)

    eff = pipe(
        effect.service(Config),
        effect.provide(config_layer),
    )

    result = effect.run_sync(eff)
    assert result is config


@pytest.mark.asyncio
async def test_succeed_provides_service_async() -> None:
    """A layer.succeed layer can be provided to an async effect."""
    config = Config("DEBUG")
    config_layer = layer.succeed(Config, config)

    eff = pipe(
        effect.service(Config),
        effect.provide(config_layer),
    )

    result = await effect.run_async(eff)
    assert result is config


def test_succeed_with_pipe_effect_chain() -> None:
    """A layer.succeed layer works with a chained effect."""
    db = Database("postgres://localhost/test")
    db_layer = layer.succeed(Database, db)

    eff = pipe(
        effect.service(Database),
        effect.map(lambda d: d.url),
        effect.provide(db_layer),
    )

    result = effect.run_sync(eff)
    assert result == "postgres://localhost/test"


def test_succeed_layer_is_frozen() -> None:
    """Layer is immutable."""
    config = Config("INFO")
    config_layer = layer.succeed(Config, config)

    with pytest.raises((AttributeError, TypeError)):
        config_layer._effect = None  # type: ignore[misc]


def test_succeed_context_provide_still_works() -> None:
    """Providing a plain Context still works after overloading provide."""
    db = Database("postgres://localhost/test")
    ctx = context.make((Database, db))

    eff = pipe(
        effect.service(Database),
        effect.provide(ctx),
    )

    result = effect.run_sync(eff)
    assert result is db
