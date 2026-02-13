"""Tests for the Context module."""

import pytest

from pyfect import context


class Database:
    def __init__(self, url: str) -> None:
        self.url = url


class Logger:
    def __init__(self, name: str) -> None:
        self.name = name


class Cache:
    def __init__(self, size: int) -> None:
        self.size = size


def test_empty_context() -> None:
    """Test that empty() creates a context with no services."""
    ctx = context.empty()
    assert ctx._services == {}


def test_make_single_service() -> None:
    """Test that make() with one pair stores the service."""
    db = Database("postgres://localhost/test")
    ctx = context.make((Database, db))

    result = context.get(ctx, Database)
    assert result is db


def test_make_two_services() -> None:
    """Test that make() with two pairs stores both services."""
    db = Database("postgres://localhost/test")
    log = Logger("app")
    ctx = context.make((Database, db), (Logger, log))

    assert context.get(ctx, Database) is db
    assert context.get(ctx, Logger) is log


def test_make_three_services() -> None:
    """Test that make() with three pairs stores all services."""
    db = Database("postgres://localhost/test")
    log = Logger("app")
    cache = Cache(256)
    ctx = context.make((Database, db), (Logger, log), (Cache, cache))

    assert context.get(ctx, Database) is db
    assert context.get(ctx, Logger) is log
    assert context.get(ctx, Cache) is cache


def test_add_to_empty_context() -> None:
    """Test that add() adds a service to an empty context."""
    db = Database("postgres://localhost/test")
    ctx = context.add(Database, db)(context.empty())

    assert context.get(ctx, Database) is db


def test_add_to_existing_context() -> None:
    """Test that add() adds a service without removing existing ones."""
    db = Database("postgres://localhost/test")
    log = Logger("app")

    ctx = context.add(Logger, log)(context.make((Database, db)))

    assert context.get(ctx, Database) is db
    assert context.get(ctx, Logger) is log


def test_add_is_pure() -> None:
    """Test that add() does not mutate the original context."""
    db = Database("postgres://localhost/test")
    log = Logger("app")
    original = context.make((Database, db))

    context.add(Logger, log)(original)

    with pytest.raises(context.MissingServiceError):
        context.get(original, Logger)


def test_get_missing_service_raises() -> None:
    """Test that get() raises MissingServiceError when service is absent."""
    ctx = context.empty()

    with pytest.raises(context.MissingServiceError) as exc_info:
        context.get(ctx, Database)

    assert exc_info.value.tag is Database


def test_missing_service_error_message() -> None:
    """Test that MissingServiceError has a descriptive message."""
    ctx = context.empty()

    with pytest.raises(context.MissingServiceError, match="Database"):
        context.get(ctx, Database)


def test_context_is_immutable() -> None:
    """Test that Context is frozen (immutable)."""
    ctx = context.empty()

    with pytest.raises((AttributeError, TypeError)):
        ctx._services = {}  # type: ignore[misc]
