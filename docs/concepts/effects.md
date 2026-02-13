# Effects

## What is an Effect?

An `Effect[A, E, R]` is a **lazy description of a computation**. It declares what a piece of work _will_ do without actually doing it. Execution only happens when you explicitly run it with the runtime.

```python
from pyfect import effect

# This does nothing yet — it's just a description
eff = effect.sync(lambda: print("Hello"))

# This executes it
effect.run_sync(eff)  # Hello
```

The three type parameters are:

| Parameter | Meaning | Default |
|-----------|---------|---------|
| `A` | The success value type | — |
| `E` | The error type | `Never` |
| `R` | The required context type | `Never` |

`E = Never` means the effect cannot fail. `R = Never` means no context is required. Both can be omitted when using the defaults:

```python
effect.Effect[int]        # succeeds with int, cannot fail, no context
effect.Effect[int, str]   # succeeds with int, fails with str, no context
effect.Effect[int, str, MyDependency]  # full form
```

## Why lazy?

Laziness separates _description_ from _execution_. This means you can build up complex pipelines, pass effects around, and decide when and how to run them — all without triggering any side effects prematurely.

```python
from pyfect import effect

# Build a pipeline — nothing executes yet
pipeline = effect.sync(lambda: 42)

# Run it once
effect.run_sync(pipeline)  # 42

# Run it again — the computation runs fresh
effect.run_sync(pipeline)  # 42
```

## Creating effects

### `succeed` and `fail`

The simplest constructors — wrap an already-known value or error:

```python
from pyfect import effect

ok = effect.succeed(42)        # Effect[int]
err = effect.fail("not found") # Effect[Never, str]
```

### `sync` and `async_`

Wrap a computation that has not run yet. The thunk is only called when the effect is executed:

```python
import asyncio
from pyfect import effect

# Synchronous
eff = effect.sync(lambda: expensive_computation())

# Asynchronous
eff = effect.async_(lambda: asyncio.sleep(1))
```

These do **not** catch exceptions. If the thunk raises, the exception propagates out of `run_sync` or `run_async`.

### `try_sync` and `try_async`

Like `sync` and `async_`, but exceptions are caught and converted into effect errors:

```python
from pyfect import effect

eff = effect.try_sync(lambda: int("not a number"))

result = effect.run_sync_exit(eff)

match result:
    case effect.Success(value):
        print(value)
    case effect.Failure(error):
        print(type(error).__name__)  # ValueError
```

The error type becomes `Exception` since any exception may be raised.

### `suspend`

Defers the _creation_ of an effect until runtime. Useful when you need to capture fresh state on each execution:

```python
from pyfect import effect

class Counter:
    def __init__(self) -> None:
        self.i = 0

    def increment(self) -> int:
        self.i += 1
        return self.i

counter = Counter()

# Bad — effect created once, captures the result of the first increment
bad = effect.succeed(counter.increment())
effect.run_sync(bad)  # 1
effect.run_sync(bad)  # 1 (same effect, same value)

# Good — effect created fresh each time
good = effect.suspend(lambda: effect.succeed(counter.increment()))
effect.run_sync(good)  # 2
effect.run_sync(good)  # 3 (fresh effect, fresh value)
```

## The context parameter `R`

The third type parameter `R` represents a required context — dependencies that the effect needs but does not create itself. This is reserved for a future release. For now, all effects use `R = Never`, meaning no context is required.
