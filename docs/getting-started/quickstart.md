# Quickstart

This guide walks you through the core ideas of pyfect in a few minutes.

## Your first effect

Effects are descriptions of work. Nothing runs until you explicitly execute them.

```python
from pyfect import effect

eff = effect.succeed(42)
result = effect.run_sync(eff)
print(result)  # 42
```

`effect.succeed` creates an effect that succeeds with a value. `effect.run_sync` executes it.

## Lazy effects

Unlike `succeed`, `sync` defers execution until the effect is run:

```python
import time
from pyfect import effect

eff = effect.sync(lambda: time.time())
# Nothing has happened yet

result = effect.run_sync(eff)
print(result)  # current timestamp, evaluated now
```

## Composing effects with pipe

Use `pipe` to build effect pipelines. Each step receives the output of the previous one:

```python
from pyfect import effect, pipe

result = pipe(
    effect.succeed(10),
    effect.map(lambda x: x * 2),
    effect.map(lambda x: x + 5),
)

print(effect.run_sync(result))  # 25
```

Use `flat_map` when the next step itself returns an effect:

```python
from pyfect import effect, pipe

def safe_divide(a: float, b: float) -> effect.Effect[float, str]:
    if b == 0:
        return effect.fail("Division by zero")
    return effect.succeed(a / b)

result = pipe(
    effect.succeed(10.0),
    effect.flat_map(lambda x: safe_divide(x, 2)),
    effect.flat_map(lambda x: safe_divide(x, 2)),
)

print(effect.run_sync(result))  # 2.5
```

## Handling errors

By default `run_sync` raises on failure. Use `run_sync_exit` to get an `Exit` value instead — a discriminated union of `Success` and `Failure`:

```python
from pyfect import effect

result = effect.run_sync_exit(safe_divide(10, 0))

match result:
    case effect.Success(value):
        print(f"Got: {value}")
    case effect.Failure(error):
        print(f"Error: {error}")  # Error: Division by zero
```

This keeps errors as values rather than exceptions, making them explicit and composable.

## Working with Option

`Option` represents values that may or may not be present — a cleaner alternative to `None` checks:

```python
from pyfect import option, pipe

def find_user(user_id: int) -> option.Option[str]:
    users = {1: "Alice", 2: "Bob"}
    return option.from_optional(users.get(user_id))

result = pipe(
    find_user(1),
    option.map(lambda name: name.upper()),
    option.get_or_else(lambda: "Unknown"),
)

print(result)  # ALICE

result = pipe(
    find_user(99),
    option.map(lambda name: name.upper()),
    option.get_or_else(lambda: "Unknown"),
)

print(result)  # Unknown
```

## Next steps

- [Effects](../concepts/effects.md) — understand the effect type in depth
- [Error Handling](../concepts/errors.md) — Exit, map_error, and error composition
- [Option](../concepts/option.md) — the full Option API
- [API Reference](../api/effect.md) — complete function reference
