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
