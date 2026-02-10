# pyfect

**Structured effects for modern Python**

Python is being used to build systems far larger and more concurrent than it was originally designed for. Async is now unavoidable, yet error handling, resource management, and concurrency remain ad-hoc and fragile. Exceptions leak everywhere. Background tasks escape. The sync/async boundary infects entire codebases.

**pyfect** exists to make this situation survivable.

It provides a small, opinionated core for describing effects explicitly, handling errors as values, and enforcing structured concurrency, without turning Python into something unrecognizable.

## What pyfect is

- A **Python-native effect system** inspired by functional programming, not a port of another language
- A **single execution model** that can compose synchronous and asynchronous work
- **Explicit errors** that compose instead of exploding control flow
- **Optional values** modelled with a first-class `Option` type
- A **runtime-first design** where safety is enforced at execution boundaries

pyfect favors clarity, discipline, and correctness over convenience magic.

## What pyfect is not

- Not a framework
- Not a replacement for `asyncio`, Trio, or AnyIO
- Not "pure FP" or academic
- Not decorator-driven async magic
- Not a grab-bag of monadic utilities

pyfect does not attempt to encode the entire program in types, eliminate exceptions everywhere, or abstract away Python's runtime model.

## Design philosophy

### Safety over convenience

If an operation can fail, it should say so. If resources are acquired, their lifetime should be explicit.

pyfect intentionally avoids APIs that:

- swallow errors
- rely on implicit global state
- hide sync/async boundaries

### Effects describe, runtimes decide

Effects are descriptions of work. Execution is centralized and controlled. Side effects only happen at the boundary, where they can be supervised, cancelled, logged, or traced.

### Influences

pyfect takes direct inspiration from [Effect](https://effect.website) — particularly its explicit error channels, pipe-based composition, and the `Option` and `Either` types. However, pyfect is not a port. Where Effect works around TypeScript's limitations, pyfect embraces Python's strengths: structural pattern matching, native async/await, and clean module namespacing.

Rust's influence shows in the treatment of errors as values (`Result`-style `Exit` types) and the preference for making failure explicit at the type level.

### Small core, honest utilities

The core of pyfect is intentionally small. Utilities are built on top but only when they preserve explicit failure and resource safety.

## Status

!!! warning "Alpha"
    pyfect is functional and usable, but the API is not yet stable. Breaking changes may occur in any release.

    Expect opinions. Expect discipline.

## Quick Example

```python
from pyfect import effect, pipe

# Define an effect that might fail
def divide(a: int, b: int) -> effect.Effect[float, str]:
    if b == 0:
        return effect.fail("Division by zero")
    return effect.succeed(a / b)

# Compose effects using pipe
result = pipe(
    divide(10, 2),
    effect.flat_map(lambda x: divide(x, 2)),
    effect.map(lambda x: x * 2),
)

# Run the effect and get an Exit value
exit_value = effect.run_sync_exit(result)

match exit_value:
    case effect.Success(value):
        print(f"Result: {value}")
    case effect.Failure(error):
        print(f"Error: {error}")
```

## Installation

```bash
pip install pyfect
```

!!! note "Python Version Requirement"
    pyfect requires Python 3.13 or later.

## Next Steps

- [Getting Started](getting-started/installation.md) - Install pyfect and run your first effect
- [Core Concepts](concepts/effects.md) - Understand the foundational ideas
- [API Reference](api/effect.md) - Explore the complete API
- [Roadmap](roadmap.md) - See what is coming next

## License

MIT
