"""
Interop — conversions between Effect and other pyfect types (Either, Option).
"""

from collections.abc import Callable
from typing import Never

import pyfect.either as either_module
import pyfect.option as option_module
from pyfect.primitives import Absorb, Effect, Fail, Map, Succeed


def from_option[A, E](
    error: Callable[[], E],
) -> Callable[[option_module.Option[A]], Effect[A, E]]:
    """
    Convert an Option into an Effect.

    Some(value) becomes a successful effect with that value.
    Nothing becomes a failed effect using the provided error thunk.

    The error thunk is only called when the Option is Nothing.

    Example:
        ```python
        from pyfect import option, pipe
        pipe(option.some(42), from_option(lambda: "not found"))    # succeeds with 42
        pipe(option.nothing(), from_option(lambda: "not found"))   # fails with "not found"
        ```
    """

    def _from_option(opt: option_module.Option[A]) -> Effect[A, E]:
        if isinstance(opt, option_module.Some):
            return Succeed(opt.value)
        return Fail(error())

    return _from_option


def from_either[R, L](e: either_module.Either[R, L]) -> Effect[R, L]:
    """
    Convert an Either into an Effect.

    Right(value) becomes a successful effect with that value.
    Left(value) becomes a failed effect with that value as the error.

    Example:
        ```python
        from pyfect import either
        from_either(either.right(42))    # succeeds with 42
        from_either(either.left("oops")) # fails with "oops"
        ```
    """
    match e:
        case either_module.Right(value):
            return Succeed(value)
        case either_module.Left(value):
            return Fail(value)
        case _:  # pragma: no cover
            msg = f"Unexpected Either variant: {type(e).__name__}"
            raise AssertionError(msg)


def option[A, E, R](eff: Effect[A, E, R]) -> Effect[option_module.Option[A], Never, R]:
    """
    Absorb failures into the success channel as Option values.

    Transforms Effect[A, E, R] into Effect[Option[A], Never, R].
    A successful effect wraps its value in Some; a failed effect maps to
    Nothing (the error is discarded). The resulting effect can never fail.

    Example:
        ```python
        from pyfect import effect

        effect.run_sync(effect.option(effect.succeed(42)))   # Some(value=42)
        effect.run_sync(effect.option(effect.fail("oops")))  # Nothing()
        ```
    """

    def _to_option(e: either_module.Either[A, E]) -> option_module.Option[A]:
        if isinstance(e, either_module.Right):
            return option_module.Some(e.value)
        return option_module.NOTHING

    return Map(Absorb(eff), _to_option)


def either[A, E, R](eff: Effect[A, E, R]) -> Effect[either_module.Either[A, E], Never, R]:
    """
    Absorb failures into the success channel as Either values.

    Transforms Effect[A, E, R] into Effect[Either[A, E], Never, R].
    A successful effect wraps its value in Right; a failed effect wraps its
    error in Left. The resulting effect can never fail.

    Use this to handle both success and failure within a pipeline, for
    example by following up with map_ and either.match_.

    Example:
        ```python
        from pyfect import effect, either, pipe

        program = effect.fail("oops")  # Effect[Never, str, Never]

        recovered = pipe(
            program,
            effect.either,              # Effect[Either[Never, str], Never, Never]
            effect.map_(either.match_(
                on_left=lambda e: f"Recovered: {e}",
                on_right=lambda v: str(v),
            )),
        )

        result = effect.run_sync(recovered)  # "Recovered: oops"
        ```
    """
    return Absorb(eff)


__all__ = [
    "either",
    "from_either",
    "from_option",
    "option",
]
