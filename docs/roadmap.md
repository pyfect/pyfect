# Roadmap

pyfect is in early development. The core effect system and `Option` type are stable and ready to use. This page outlines what is coming next, roughly in priority order.

## Either

`Either[L, R]` is a pure data type representing a value that is either a `Left` (conventionally the failure case) or a `Right` (the success case). Unlike `Effect`, `Either` is not lazy — it is a plain value you can pattern match on immediately, with no runtime required.

```python
# Planned API
from pyfect import either

either.right(42)        # Right(value=42)
either.left("oops")     # Left(value="oops")
```

`Either` is the right tool when you have a synchronous computation that can fail but does not need the full effect machinery. It will interoperate with `Effect` similarly to how `Option` does today.

## Context & Dependency Injection

The `R` type parameter in `Effect[A, E, R]` is already part of the type signature but currently always `None`. The plan is to give it meaning: `R` declares the services an effect requires to run.

This enables dependency injection without globals — effects declare their requirements in the type, and the runtime ensures they are satisfied before the effect runs. The design will follow Effect's `Layer` model for composing and providing services.

```python
# Planned API
from pyfect import effect

class Database: ...
class Logger: ...

def find_user(user_id: int) -> effect.Effect[str, NotFoundError, Database]:
    ...
```

## Error Recovery

Practical error handling combinators that are missing from the current release:

- `catch` — recover from a specific error by returning a new effect
- `catch_all` — recover from any failure
- `retry` — re-run an effect with a configurable policy (fixed delay, exponential backoff, max attempts)
- `timeout` — fail an effect if it does not complete within a given duration

## Structured Concurrency & Primitives

The largest milestone. Once fibers exist, the full set of concurrency primitives follows:

- **Fiber** — a lightweight unit of concurrent execution with structured lifetime
- **Cancellation** — automatic propagation of cancellation through fiber hierarchies
- **Deferred** — a single-value async variable, set once and awaited by many
- **Queue** — a bounded or unbounded async queue for producer/consumer workflows
- **PubSub** — a broadcast channel for fan-out messaging
- **Semaphore** — rate-limiting and mutual exclusion
- **Latch** — a countdown latch for synchronising a group of fibers
- **Scope & bracket** — structured resource management with guaranteed cleanup on success, failure, or cancellation

## Effect Combinators

Quality-of-life combinators for working with collections of effects:

- `zip_with` — combine two effects into one, failing if either fails
- `all` — run a list or dict of effects and collect results
- `race` — run multiple effects and return the first to complete
