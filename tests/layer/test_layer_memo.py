"""Tests for layer memoization and layer.fresh."""

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


# ============================================================================
# Diamond dependency memoization
# ============================================================================


def test_diamond_dependency_constructs_shared_layer_once() -> None:
    """A shared layer appearing in two branches of a diamond is built only once."""
    calls: list[str] = []

    def make_config() -> Config:
        calls.append("config")
        return Config("INFO")

    config_layer = layer.sync(Config, make_config)

    logger_layer = pipe(
        layer.effect(Logger, pipe(effect.service(Config), effect.map_(lambda c: Logger(c.level)))),
        layer.provide(config_layer),
    )
    db_layer = pipe(
        layer.effect(
            Database, pipe(effect.service(Config), effect.map_(lambda c: Database(c.level)))
        ),
        layer.provide(config_layer),
    )

    app_layer = layer.merge(logger_layer, db_layer)

    eff = pipe(
        effect.service(Logger, Database),
        effect.provide(app_layer),
    )

    _logger, _db = effect.run_sync(eff)
    assert calls == ["config"], f"Config constructed {len(calls)} time(s), expected 1"


@pytest.mark.asyncio
async def test_diamond_dependency_constructs_shared_layer_once_async() -> None:
    """Same diamond test but with the async runtime."""
    calls: list[str] = []

    def make_config() -> Config:
        calls.append("config")
        return Config("INFO")

    config_layer = layer.sync(Config, make_config)

    logger_layer = pipe(
        layer.effect(Logger, pipe(effect.service(Config), effect.map_(lambda c: Logger(c.level)))),
        layer.provide(config_layer),
    )
    db_layer = pipe(
        layer.effect(
            Database, pipe(effect.service(Config), effect.map_(lambda c: Database(c.level)))
        ),
        layer.provide(config_layer),
    )

    app_layer = layer.merge(logger_layer, db_layer)

    eff = pipe(
        effect.service(Logger, Database),
        effect.provide(app_layer),
    )

    _logger, _db = await effect.run_async(eff)
    assert calls == ["config"], f"Config constructed {len(calls)} time(s), expected 1"


def test_same_layer_used_twice_in_merge_is_built_once() -> None:
    """A layer merged with itself constructs the service exactly once."""
    calls: list[str] = []

    def make_config() -> Config:
        calls.append("config")
        return Config("INFO")

    config_layer = layer.sync(Config, make_config)
    merged = layer.merge(config_layer, config_layer)

    eff = pipe(
        effect.service(Config),
        effect.provide(merged),
    )

    effect.run_sync(eff)
    assert calls == ["config"]


def test_memoization_is_per_run_call() -> None:
    """Memo state does not leak between separate run_sync calls."""
    calls: list[str] = []

    def make_config() -> Config:
        calls.append("config")
        return Config("INFO")

    config_layer = layer.sync(Config, make_config)

    eff = pipe(
        effect.service(Config),
        effect.provide(config_layer),
    )

    effect.run_sync(eff)
    effect.run_sync(eff)
    assert calls == ["config", "config"]


# ============================================================================
# layer.fresh
# ============================================================================


def test_fresh_opts_out_of_memoization() -> None:
    """layer.fresh produces a separate construction for each use."""
    calls: list[str] = []

    def make_config() -> Config:
        calls.append("config")
        return Config("INFO")

    base = layer.sync(Config, make_config)

    logger_layer = pipe(
        layer.effect(Logger, pipe(effect.service(Config), effect.map_(lambda c: Logger(c.level)))),
        layer.provide(layer.fresh(base)),
    )
    db_layer = pipe(
        layer.effect(
            Database, pipe(effect.service(Config), effect.map_(lambda c: Database(c.level)))
        ),
        layer.provide(layer.fresh(base)),
    )

    app_layer = layer.merge(logger_layer, db_layer)

    eff = pipe(
        effect.service(Logger, Database),
        effect.provide(app_layer),
    )

    effect.run_sync(eff)
    assert len(calls) == 2, f"Expected 2 constructions with fresh, got {len(calls)}"  # noqa: PLR2004


@pytest.mark.asyncio
async def test_fresh_opts_out_of_memoization_async() -> None:
    """layer.fresh forces separate construction in the async runtime too."""
    calls: list[str] = []

    def make_config() -> Config:
        calls.append("config")
        return Config("INFO")

    base = layer.sync(Config, make_config)

    logger_layer = pipe(
        layer.effect(Logger, pipe(effect.service(Config), effect.map_(lambda c: Logger(c.level)))),
        layer.provide(layer.fresh(base)),
    )
    db_layer = pipe(
        layer.effect(
            Database, pipe(effect.service(Config), effect.map_(lambda c: Database(c.level)))
        ),
        layer.provide(layer.fresh(base)),
    )

    app_layer = layer.merge(logger_layer, db_layer)

    eff = pipe(
        effect.service(Logger, Database),
        effect.provide(app_layer),
    )

    await effect.run_async(eff)
    assert len(calls) == 2  # noqa: PLR2004


def test_fresh_does_not_affect_original_layer_identity() -> None:
    """layer.fresh returns a distinct layer; the original is unchanged."""
    base = layer.sync(Config, lambda: Config("INFO"))
    fresh_copy = layer.fresh(base)

    assert fresh_copy is not base
    assert fresh_copy._id != base._id


# ============================================================================
# Memoization correctness
# ============================================================================


def test_memoized_value_is_the_same_instance() -> None:
    """Both dependents receive the exact same service instance via memoization."""
    config_layer = layer.sync(Config, lambda: Config("INFO"))

    _logger_layer = pipe(
        layer.effect(Logger, pipe(effect.service(Config), effect.map_(lambda c: Logger(c.level)))),
        layer.provide(config_layer),
    )
    _db_layer = pipe(
        layer.effect(
            Database, pipe(effect.service(Config), effect.map_(lambda c: Database(c.level)))
        ),
        layer.provide(config_layer),
    )

    instances: list[Config] = []

    def capture_config(c: Config) -> Config:
        instances.append(c)
        return c

    capturing_logger = pipe(
        layer.effect(
            Logger,
            pipe(
                effect.service(Config),
                effect.map_(lambda c: (capture_config(c), Logger(c.level))[1]),
            ),
        ),
        layer.provide(config_layer),
    )
    capturing_db = pipe(
        layer.effect(
            Database,
            pipe(
                effect.service(Config),
                effect.map_(lambda c: (capture_config(c), Database(c.level))[1]),
            ),
        ),
        layer.provide(config_layer),
    )

    app_layer = layer.merge(capturing_logger, capturing_db)

    eff = pipe(
        effect.service(Logger, Database),
        effect.provide(app_layer),
    )

    effect.run_sync(eff)
    assert len(instances) == 2  # noqa: PLR2004
    assert instances[0] is instances[1], "Both dependents should receive the same Config instance"


# ============================================================================
# Exit runner coverage (run_sync_exit / run_async_exit with layers)
# ============================================================================


def test_run_sync_exit_memoizes_shared_layer() -> None:
    """_run_sync_exit memoizes a shared layer (covers MemoizedEffect cache-hit path)."""
    calls: list[str] = []

    def make_config() -> Config:
        calls.append("config")
        return Config("INFO")

    config_layer = layer.sync(Config, make_config)

    logger_layer = pipe(
        layer.effect(Logger, pipe(effect.service(Config), effect.map_(lambda c: Logger(c.level)))),
        layer.provide(config_layer),
    )
    db_layer = pipe(
        layer.effect(
            Database, pipe(effect.service(Config), effect.map_(lambda c: Database(c.level)))
        ),
        layer.provide(config_layer),
    )

    eff = pipe(
        effect.service(Logger, Database),
        effect.provide(layer.merge(logger_layer, db_layer)),
    )

    effect.run_sync_exit(eff)
    assert calls == ["config"]


def test_run_sync_exit_memoized_failure_path() -> None:
    """_run_sync_exit propagates layer construction failure as Exit.Failure."""

    class BuildError(Exception):
        pass

    failing_layer = layer.effect(Config, effect.fail(BuildError("boom")))

    eff = pipe(
        effect.service(Config),
        effect.provide(failing_layer),
    )

    result = effect.run_sync_exit(eff)
    match result:
        case effect.Failure(e):
            assert isinstance(e, BuildError)
        case effect.Success(_):
            msg = "Expected failure"
            raise AssertionError(msg)


@pytest.mark.asyncio
async def test_run_async_exit_memoizes_shared_layer() -> None:
    """_run_async_exit memoizes a shared layer (covers MemoizedEffect cache-hit path)."""
    calls: list[str] = []

    def make_config() -> Config:
        calls.append("config")
        return Config("INFO")

    config_layer = layer.sync(Config, make_config)

    logger_layer = pipe(
        layer.effect(Logger, pipe(effect.service(Config), effect.map_(lambda c: Logger(c.level)))),
        layer.provide(config_layer),
    )
    db_layer = pipe(
        layer.effect(
            Database, pipe(effect.service(Config), effect.map_(lambda c: Database(c.level)))
        ),
        layer.provide(config_layer),
    )

    eff = pipe(
        effect.service(Logger, Database),
        effect.provide(layer.merge(logger_layer, db_layer)),
    )

    await effect.run_async_exit(eff)
    assert calls == ["config"]


@pytest.mark.asyncio
async def test_run_async_exit_memoized_failure_path() -> None:
    """_run_async_exit propagates layer construction failure as Exit.Failure."""

    class BuildError(Exception):
        pass

    failing_layer = layer.effect(Config, effect.fail(BuildError("boom")))

    eff = pipe(
        effect.service(Config),
        effect.provide(failing_layer),
    )

    result = await effect.run_async_exit(eff)
    match result:
        case effect.Failure(e):
            assert isinstance(e, BuildError)
        case effect.Success(_):
            msg = "Expected failure"
            raise AssertionError(msg)
