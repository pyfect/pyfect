"""
Context - a typed container for service implementations.

Context maps service tags (classes) to their implementations and is
passed to the runtime when providing services to an effect.
"""

from dataclasses import dataclass, field
from typing import Any, Never, Protocol, cast, overload


class MissingServiceError(Exception):
    """Raised when a service is looked up that was not provided in the context."""

    def __init__(self, tag: type) -> None:
        super().__init__(
            f"Service '{tag.__name__}' not found in context. Did you forget to provide it?"
        )
        self.tag = tag


@dataclass(frozen=True)
class Context[S]:
    """A typed container mapping service tags to their implementations.

    The type parameter S represents the union of all service types
    currently held in the context. Use the module-level functions to
    construct and manipulate contexts.
    """

    _services: dict[type, Any] = field(default_factory=dict)


class AddCallable[T](Protocol):
    def __call__[S](self, ctx: Context[S]) -> Context[S | T]: ...


# ============================================================================
# Constructors
# ============================================================================


def empty() -> Context[Never]:
    """Create an empty context with no services."""
    return Context()


@overload
def make[S1](s1: tuple[type[S1], S1], /) -> Context[S1]: ...


@overload
def make[S1, S2](
    s1: tuple[type[S1], S1],
    s2: tuple[type[S2], S2],
    /,
) -> Context[S1 | S2]: ...


@overload
def make[S1, S2, S3](
    s1: tuple[type[S1], S1],
    s2: tuple[type[S2], S2],
    s3: tuple[type[S3], S3],
    /,
) -> Context[S1 | S2 | S3]: ...


@overload
def make[S1, S2, S3, S4](
    s1: tuple[type[S1], S1],
    s2: tuple[type[S2], S2],
    s3: tuple[type[S3], S3],
    s4: tuple[type[S4], S4],
    /,
) -> Context[S1 | S2 | S3 | S4]: ...


@overload
def make[S1, S2, S3, S4, S5](
    s1: tuple[type[S1], S1],
    s2: tuple[type[S2], S2],
    s3: tuple[type[S3], S3],
    s4: tuple[type[S4], S4],
    s5: tuple[type[S5], S5],
    /,
) -> Context[S1 | S2 | S3 | S4 | S5]: ...


@overload
def make[S1, S2, S3, S4, S5, S6](
    s1: tuple[type[S1], S1],
    s2: tuple[type[S2], S2],
    s3: tuple[type[S3], S3],
    s4: tuple[type[S4], S4],
    s5: tuple[type[S5], S5],
    s6: tuple[type[S6], S6],
    /,
) -> Context[S1 | S2 | S3 | S4 | S5 | S6]: ...


@overload
def make[S1, S2, S3, S4, S5, S6, S7](
    s1: tuple[type[S1], S1],
    s2: tuple[type[S2], S2],
    s3: tuple[type[S3], S3],
    s4: tuple[type[S4], S4],
    s5: tuple[type[S5], S5],
    s6: tuple[type[S6], S6],
    s7: tuple[type[S7], S7],
    /,
) -> Context[S1 | S2 | S3 | S4 | S5 | S6 | S7]: ...


@overload
def make[S1, S2, S3, S4, S5, S6, S7, S8](
    s1: tuple[type[S1], S1],
    s2: tuple[type[S2], S2],
    s3: tuple[type[S3], S3],
    s4: tuple[type[S4], S4],
    s5: tuple[type[S5], S5],
    s6: tuple[type[S6], S6],
    s7: tuple[type[S7], S7],
    s8: tuple[type[S8], S8],
    /,
) -> Context[S1 | S2 | S3 | S4 | S5 | S6 | S7 | S8]: ...


@overload
def make[S1, S2, S3, S4, S5, S6, S7, S8, S9](
    s1: tuple[type[S1], S1],
    s2: tuple[type[S2], S2],
    s3: tuple[type[S3], S3],
    s4: tuple[type[S4], S4],
    s5: tuple[type[S5], S5],
    s6: tuple[type[S6], S6],
    s7: tuple[type[S7], S7],
    s8: tuple[type[S8], S8],
    s9: tuple[type[S9], S9],
    /,
) -> Context[S1 | S2 | S3 | S4 | S5 | S6 | S7 | S8 | S9]: ...


@overload
def make[S1, S2, S3, S4, S5, S6, S7, S8, S9, S10](
    s1: tuple[type[S1], S1],
    s2: tuple[type[S2], S2],
    s3: tuple[type[S3], S3],
    s4: tuple[type[S4], S4],
    s5: tuple[type[S5], S5],
    s6: tuple[type[S6], S6],
    s7: tuple[type[S7], S7],
    s8: tuple[type[S8], S8],
    s9: tuple[type[S9], S9],
    s10: tuple[type[S10], S10],
    /,
) -> Context[S1 | S2 | S3 | S4 | S5 | S6 | S7 | S8 | S9 | S10]: ...


def make(*args: tuple[type, Any]) -> Context[Any]:
    """Create a context from one or more (tag, implementation) pairs."""
    return Context(dict(args))


# ============================================================================
# Operations
# ============================================================================


def add[T](tag: type[T], impl: T) -> AddCallable[T]:
    """Return a function that adds a service to an existing context.

    Designed to be used with pipe:

    Example:
        ```python
        from pyfect import context, pipe

        ctx = pipe(
            context.empty(),
            context.add(Database, db_impl),
            context.add(Logger, logger_impl),
        )
        # ctx: Context[Database | Logger]
        ```
    """

    def _apply(ctx: Context[Any]) -> Context[Any]:
        return Context({**ctx._services, tag: impl})

    return cast(AddCallable[T], _apply)


def merge[S1, S2](ctx1: Context[S1], ctx2: Context[S2]) -> Context[S1 | S2]:
    """Combine two contexts into one, containing all services from both.

    If the same tag exists in both, ctx2's value wins.

    Example:
        ```python
        from pyfect import context, pipe

        ctx = context.merge(
            context.make((Config, config_impl)),
            context.make((Logger, logger_impl)),
        )
        # ctx: Context[Config | Logger]
        ```
    """
    return Context({**ctx1._services, **ctx2._services})


def get[S, T](ctx: Context[S], tag: type[T]) -> T:
    """Look up a service by tag. Raises MissingServiceError if not found."""
    try:
        return ctx._services[tag]  # type: ignore[return-value]
    except KeyError:
        raise MissingServiceError(tag) from None


__all__ = [
    "AddCallable",
    "Context",
    "MissingServiceError",
    "add",
    "empty",
    "get",
    "make",
    "merge",
]
