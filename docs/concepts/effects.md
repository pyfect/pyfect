# Effects

!!! warning "Documentation In Progress"
    This section is being developed. For now, refer to the [test suite](https://github.com/pyfect/pyfect/tree/main/tests) for examples.

## What is an Effect?

An `Effect[E, A, R]` is a description of a computation that:

- May produce a value of type `A` on success
- May fail with an error of type `E`
- May require a context of type `R`
- Is lazy - nothing happens until you run it

## Creating Effects

```python
from pyfect import effect

# Success
success = effect.succeed(42)

# Failure
failure = effect.fail("error message")

# Sync computation
sync_eff = effect.sync(lambda: expensive_computation())

# Async computation
async_eff = effect.async_(lambda: async_operation())
```

See the tests for more examples.
