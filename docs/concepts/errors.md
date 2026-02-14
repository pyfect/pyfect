# Error Handling

## Errors as values

In most Python code, errors are exceptions — they interrupt control flow, skip over code, and must be caught somewhere up the call stack or they crash the program. This makes error handling easy to forget and hard to reason about.

In pyfect, errors are values. An effect that can fail declares it in its type:

```python
from pyfect import effect

def parse_int(s: str) -> effect.Effect[int, str]:
    try:
        return effect.succeed(int(s))
    except ValueError:
        return effect.fail(f"Not a number: {s}")
```

The type `Effect[int, str]` tells you upfront: this computation either produces an `int` or fails with a `str`. There is no hidden exception channel.

## Exit

When you run an effect, you get an `Exit[A, E]` — a discriminated union of `Success[A]` and `Failure[E]`:

```python
from pyfect import effect

result = effect.run_sync_exit(parse_int("42"))

match result:
    case effect.Success(value):
        print(f"Parsed: {value}")   # Parsed: 42
    case effect.Failure(error):
        print(f"Failed: {error}")
```

```python
result = effect.run_sync_exit(parse_int("oops"))

match result:
    case effect.Success(value):
        print(f"Parsed: {value}")
    case effect.Failure(error):
        print(f"Failed: {error}")   # Failed: Not a number: oops
```

`Exit[A]` — with the default `E = Never` — means the effect cannot fail.

## `run_sync` vs `run_sync_exit`

| Function | On failure |
|----------|-----------|
| `run_sync` | Raises the error as an exception |
| `run_sync_exit` | Returns `Failure(error)` |

Use `run_sync_exit` when you want to handle errors as values. Use `run_sync` at the top of your program when you are okay with exceptions propagating.

The same applies to `run_async` and `run_async_exit`.

## Transforming errors with `map_error`

`map_error` transforms the error type without changing the success path — the counterpart to `map` for the error channel:

```python
from pyfect import effect, pipe

class AppError(Exception):
    pass

result = pipe(
    parse_int("oops"),
    effect.map_error(lambda msg: AppError(msg)),
)

exit_value = effect.run_sync_exit(result)

match exit_value:
    case effect.Success(value):
        print(value)
    case effect.Failure(error):
        print(error)   # Not a number: oops
```

This is useful for converting low-level errors (strings, exceptions from third-party code) into your application's own error types at a boundary.

## Inspecting errors with `tap_error`

`tap_error` runs a side effect when the effect fails, without modifying the error. The original failure passes through unchanged:

```python
from pyfect import effect, pipe

result = pipe(
    parse_int("oops"),
    effect.tap_error(lambda e: effect.sync(lambda: print(f"Error occurred: {e}"))),
)

effect.run_sync_exit(result)
# Prints: Error occurred: Not a number: oops
# Returns: Failure("Not a number: oops")
```

Useful for logging or monitoring without altering the error flow.

## Mixing error types

When you chain effects with `flat_map`, `tap`, or `tap_error`, the function's returned effect may have a **different** error type `E2`. The resulting effect carries `E | E2` — the union of both:

```python
from pyfect import effect, pipe

def parse_int(s: str) -> effect.Effect[int, str]:
    ...

def validate_positive(n: int) -> effect.Effect[int, ValueError]:
    if n <= 0:
        return effect.fail(ValueError("must be positive"))
    return effect.succeed(n)

# Result: Effect[int, str | ValueError]
result = pipe(
    parse_int("42"),
    effect.flat_map(validate_positive),
)
```

When the function's effect can never fail (error type `Never`), the union collapses — `E | Never = E`. This is why passing `effect.succeed(...)` to `tap` does not widen the error type:

```python
# Still Effect[int, str] — tap function can't fail, so E | Never = E
result = pipe(
    parse_int("42"),
    effect.tap(lambda x: effect.sync(lambda: print(x))),
)
```

### Type inference and named functions

Lambdas work at runtime, but type checkers see the lambda parameter as the unconstrained type variable `A` until the outer effect is known. If you pass that parameter to a function with a concrete type, the checker will flag it:

```python
async def log_value(x: int) -> None:
    ...

# Type checker: "A@tap" is not assignable to "int"
effect.tap(lambda x: effect.async_(lambda: log_value(x)))(effect.succeed(42))
```

The fix is a named function with an explicit annotation, giving the type checker what it needs:

```python
from typing import Never

def do_log(x: int) -> effect.Effect[None]:
    return effect.async_(lambda: log_value(x))

effect.tap(do_log)(effect.succeed(42))  # ✓
```

### Annotating `effect.fail` in isolation

`effect.fail(e)` has no success value, so the success type `A` defaults to `Never`. That is fine inside a function whose return type gives the context:

```python
def parse_int(s: str) -> effect.Effect[int, str]:
    ...
    return effect.fail(f"Not a number: {s}")   # A inferred as int from return type
```

But when you assign the result to a variable and then chain a combinator that requires a concrete success type, the type checker sees `Effect[Never, E]` and will flag the mismatch:

```python
eff = effect.fail(ValueError("oops"))          # Effect[Never, ValueError]
mapped = effect.map(lambda x: x * 2)(eff)      # error: Operator "*" not supported for types "A@map" and "Literal[2]"
```

Fix this with an explicit annotation on the variable **and** a named function with a typed parameter (a lambda's parameter stays unconstrained as `A@map`, so the operator error persists even after annotating the variable):

```python
def double(x: int) -> int:
    return x * 2

eff: effect.Effect[int, ValueError] = effect.fail(ValueError("oops"))
mapped = effect.map(double)(eff)      # ✓
```

## Errors compose

Because errors are values, they compose naturally through pipelines. If any step fails, subsequent steps are skipped and the failure propagates through:

```python
from pyfect import effect, pipe

result = pipe(
    parse_int("42"),
    effect.flat_map(lambda x: parse_int("oops")),  # fails here
    effect.map(lambda x: x * 2),                   # skipped
)

match effect.run_sync_exit(result):
    case effect.Success(value):
        print(value)
    case effect.Failure(error):
        print(error)   # Not a number: oops
```
