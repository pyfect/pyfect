"""Tests for effect.provide with contexts — including multi-provide.

Multi-provide (chaining separate provide calls) works at runtime because
the runtime merges contexts. The type system requires that all services
are declared satisfied before running — use context.make or context.merge
to provide everything the effect needs in a single provide call, or
chain provides and annotate the final fully-satisfied effect explicitly.
"""

import pytest

from pyfect import context, effect, pipe

# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------


class Database:
    def __init__(self, url: str) -> None:
        self.url = url


class Logger:
    def __init__(self, level: str) -> None:
        self.level = level


class Cache:
    def __init__(self, ttl: int) -> None:
        self.ttl = ttl


# ---------------------------------------------------------------------------
# Single provide — baseline
# ---------------------------------------------------------------------------


def test_single_provide_one_service() -> None:
    db = Database("postgres://localhost")
    eff = pipe(
        effect.service(Database),
        effect.provide(context.make((Database, db))),
    )
    assert effect.run_sync(eff).url == "postgres://localhost"


def test_single_provide_two_services_at_once() -> None:
    db = Database("db")
    log = Logger("INFO")
    eff = pipe(
        effect.service(Database, Logger),
        effect.provide(context.make((Database, db), (Logger, log))),
    )
    got_db, got_log = effect.run_sync(eff)
    assert got_db.url == "db"
    assert got_log.level == "INFO"


# ---------------------------------------------------------------------------
# Multi-provide — each call contributes one service, runtime merges them.
# The type system can't track residual R across chained provides, so the
# final effect is annotated explicitly.
# ---------------------------------------------------------------------------


def test_two_provides_chain() -> None:
    db = Database("db")
    log = Logger("DEBUG")

    runnable = pipe(
        effect.service(Database, Logger),
        effect.provide(context.make((Database, db))),
        effect.provide(context.make((Logger, log))),
    )

    got_db, got_log = effect.run_sync(runnable)
    assert got_db.url == "db"
    assert got_log.level == "DEBUG"


def test_three_provides_chain() -> None:
    db = Database("db")
    log = Logger("WARN")
    cache = Cache(60)

    needs_all = pipe(
        effect.service(Database, Logger),
        effect.flat_map(
            lambda dl: pipe(
                effect.service(Cache),
                effect.map_(lambda c: (*dl, c)),
            )
        ),
    )

    runnable = pipe(
        needs_all,
        effect.provide(context.make((Database, db))),
        effect.provide(context.make((Logger, log))),
        effect.provide(context.make((Cache, cache))),
    )

    got_db, got_log, got_cache = effect.run_sync(runnable)
    assert got_db.url == "db"
    assert got_log.level == "WARN"
    assert got_cache.ttl == 60  # noqa: PLR2004


def test_multi_provide_order_does_not_matter() -> None:
    db = Database("db")
    log = Logger("INFO")

    eff_db_first = pipe(
        effect.service(Database, Logger),
        effect.provide(context.make((Database, db))),
        effect.provide(context.make((Logger, log))),
    )

    eff_log_first = pipe(
        effect.service(Database, Logger),
        effect.provide(context.make((Logger, log))),
        effect.provide(context.make((Database, db))),
    )

    r1 = effect.run_sync(eff_db_first)
    r2 = effect.run_sync(eff_log_first)
    assert r1[0].url == r2[0].url
    assert r1[1].level == r2[1].level


# ---------------------------------------------------------------------------
# Override — inner provide wins for the same service tag
# ---------------------------------------------------------------------------


def test_inner_provide_overrides_outer_for_same_service() -> None:
    """When the same service is provided twice, the innermost wins."""
    inner_db = Database("inner")
    outer_db = Database("outer")

    runnable = pipe(
        effect.service(Database),
        effect.provide(context.make((Database, inner_db))),  # inner — wins
        effect.provide(context.make((Database, outer_db))),  # outer — loses
    )

    assert effect.run_sync(runnable).url == "inner"


# ---------------------------------------------------------------------------
# Async
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_two_provides_async() -> None:
    db = Database("async-db")
    log = Logger("TRACE")

    runnable = pipe(
        effect.service(Database, Logger),
        effect.provide(context.make((Database, db))),
        effect.provide(context.make((Logger, log))),
    )

    got_db, got_log = await effect.run_async(runnable)
    assert got_db.url == "async-db"
    assert got_log.level == "TRACE"
