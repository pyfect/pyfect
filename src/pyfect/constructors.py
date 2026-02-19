"""
Effect constructors — functions that create Effect values from scratch.
"""

from collections.abc import Awaitable, Callable
from typing import Never, overload

from pyfect.primitives import (
    Async,
    Effect,
    Fail,
    FlatMap,
    Map,
    Service,
    Succeed,
    Suspend,
    Sync,
    TryAsync,
    TrySync,
)


def succeed[A](value: A) -> Effect[A]:
    """
    Create an effect that succeeds with a value.

    Example:
        ```python
        eff = succeed(42)
        ```
    """
    return Succeed(value)


def fail[E, A = Never](error: E) -> Effect[A, E]:
    """
    Create an effect that fails with an error.

    Example:
        ```python
        eff = fail("Something went wrong")
        ```
    """
    return Fail(error)


def sync[A, E = Never](thunk: Callable[[], A]) -> Effect[A, E]:
    """
    Create an effect from a synchronous computation.

    The computation is not executed immediately - it's deferred until
    the effect is run by the runtime.

    Example:
        ```python
        eff = sync(lambda: print("Hello"))
        # Nothing printed yet - it's just a description
        # Will print when the effect is run
        ```
    """
    return Sync(thunk)


def async_[A, E = Never](thunk: Callable[[], Awaitable[A]]) -> Effect[A, E]:
    """
    Create an effect from an asynchronous computation.

    The computation is not executed immediately - it's deferred until
    the effect is run by the runtime.

    Note: Uses async_ (with underscore) since 'async' is a Python keyword.

    Example:
        ```python
        import asyncio
        eff = async_(lambda: asyncio.sleep(1))
        # Sleep doesn't happen yet - only when the effect is run
        ```
    """
    return Async(thunk)


def try_sync[A](thunk: Callable[[], A]) -> Effect[A, Exception]:
    """
    Create an effect from a synchronous computation that might throw.

    Exceptions are captured and converted to effect errors.

    Example:
        ```python
        eff = try_sync(lambda: int("not a number"))
        result = run_sync_exit(eff)  # Failure(ValueError(...))
        ```
    """
    return TrySync(thunk)


def try_async[A](thunk: Callable[[], Awaitable[A]]) -> Effect[A, Exception]:
    """
    Create an effect from an asynchronous computation that might throw.

    Exceptions are captured and converted to effect errors.

    Example:
        ```python
        import asyncio

        async def might_fail():
            await asyncio.sleep(0.1)
            raise ValueError("oops")

        eff = try_async(might_fail)
        result = await run_async_exit(eff)  # Failure(ValueError("oops"))
        ```
    """
    return TryAsync(thunk)


def suspend[A, E = Never, R = Never](thunk: Callable[[], Effect[A, E, R]]) -> Effect[A, E, R]:
    """
    Delay the creation of an effect until runtime.

    The thunk is called each time the effect is run, allowing for:
    - Lazy evaluation of effects
    - Re-execution of side effects on each run
    - Capturing fresh state each time

    Example:
        ```python
        i = 0
        # Bad - effect created once, i captured at creation
        bad = succeed((i := i + 1))
        run_sync(bad)  # 1
        run_sync(bad)  # 1 (same effect, same i)

        # Good - effect created fresh each run
        good = suspend(lambda: succeed((i := i + 1)))
        run_sync(good)  # 2
        run_sync(good)  # 3 (fresh effect, fresh i!)
        ```
    """
    return Suspend(thunk)


@overload
def service[S1](tag: type[S1], /) -> Effect[S1, Never, S1]: ...


@overload
def service[S1, S2](tag1: type[S1], tag2: type[S2], /) -> Effect[tuple[S1, S2], Never, S1 | S2]: ...


@overload
def service[S1, S2, S3](
    tag1: type[S1], tag2: type[S2], tag3: type[S3], /
) -> Effect[tuple[S1, S2, S3], Never, S1 | S2 | S3]: ...


@overload
def service[S1, S2, S3, S4](
    tag1: type[S1], tag2: type[S2], tag3: type[S3], tag4: type[S4], /
) -> Effect[tuple[S1, S2, S3, S4], Never, S1 | S2 | S3 | S4]: ...


@overload
def service[S1, S2, S3, S4, S5](
    tag1: type[S1], tag2: type[S2], tag3: type[S3], tag4: type[S4], tag5: type[S5], /
) -> Effect[tuple[S1, S2, S3, S4, S5], Never, S1 | S2 | S3 | S4 | S5]: ...


@overload
def service[S1, S2, S3, S4, S5, S6](
    tag1: type[S1],
    tag2: type[S2],
    tag3: type[S3],
    tag4: type[S4],
    tag5: type[S5],
    tag6: type[S6],
    /,
) -> Effect[tuple[S1, S2, S3, S4, S5, S6], Never, S1 | S2 | S3 | S4 | S5 | S6]: ...


@overload
def service[S1, S2, S3, S4, S5, S6, S7](
    tag1: type[S1],
    tag2: type[S2],
    tag3: type[S3],
    tag4: type[S4],
    tag5: type[S5],
    tag6: type[S6],
    tag7: type[S7],
    /,
) -> Effect[tuple[S1, S2, S3, S4, S5, S6], Never, S1 | S2 | S3 | S4 | S5 | S6 | S7]: ...


@overload
def service[S1, S2, S3, S4, S5, S6, S7, S8](
    tag1: type[S1],
    tag2: type[S2],
    tag3: type[S3],
    tag4: type[S4],
    tag5: type[S5],
    tag6: type[S6],
    tag7: type[S7],
    tag8: type[S8],
    /,
) -> Effect[tuple[S1, S2, S3, S4, S5, S6], Never, S1 | S2 | S3 | S4 | S5 | S6 | S7 | S8]: ...


@overload
def service[S1, S2, S3, S4, S5, S6, S7, S8, S9](
    tag1: type[S1],
    tag2: type[S2],
    tag3: type[S3],
    tag4: type[S4],
    tag5: type[S5],
    tag6: type[S6],
    tag7: type[S7],
    tag8: type[S8],
    tag9: type[S9],
    /,
) -> Effect[tuple[S1, S2, S3, S4, S5, S6], Never, S1 | S2 | S3 | S4 | S5 | S6 | S7 | S8 | S9]: ...


@overload
def service[S1, S2, S3, S4, S5, S6, S7, S8, S9, S10](
    tag1: type[S1],
    tag2: type[S2],
    tag3: type[S3],
    tag4: type[S4],
    tag5: type[S5],
    tag6: type[S6],
    tag7: type[S7],
    tag8: type[S8],
    tag9: type[S9],
    tag10: type[S10],
    /,
) -> Effect[
    tuple[S1, S2, S3, S4, S5, S6], Never, S1 | S2 | S3 | S4 | S5 | S6 | S7 | S8 | S9 | S10
]: ...


def service(*tags: type) -> Effect:  # type: ignore[type-arg, misc]
    """
    Create an effect that looks up one or more services from the context.

    For a single tag, returns the service instance directly.
    For multiple tags, returns a tuple of instances in the same order.
    The effect requires all provided tags as context.

    Example:
        ```python
        # Single service
        eff = service(Database)  # Effect[Database, Never, Database]

        # Multiple services
        eff = service(Database, Logger)  # Effect[tuple[Database, Logger], Never, Database | Logger]
        ```
    """
    if len(tags) == 1:
        return Service(tags[0])
    t1, t2, *rest = tags
    result: Effect = FlatMap(  # type: ignore[type-arg]
        Service(t1),
        lambda s1, t=t2: Map(Service(t), lambda s2: (s1, s2)),  # type: ignore[misc]
    )
    for tag in rest:
        result = FlatMap(result, lambda acc, t=tag: Map(Service(t), lambda s: (*acc, s)))  # type: ignore[misc]
    return result


__all__ = [
    "async_",
    "fail",
    "service",
    "succeed",
    "suspend",
    "sync",
    "try_async",
    "try_sync",
]
