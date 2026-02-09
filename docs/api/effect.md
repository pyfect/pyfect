# Effect API

!!! warning "Documentation In Progress"
    API documentation is being developed. For now, refer to the source code and tests.

## Creating Effects

- `effect.succeed(value)` - Create a successful effect
- `effect.fail(error)` - Create a failed effect
- `effect.sync(fn)` - Wrap a synchronous computation
- `effect.async_(fn)` - Wrap an asynchronous computation
- `effect.try_sync(fn)` - Wrap a sync computation that may throw
- `effect.try_async(fn)` - Wrap an async computation that may throw

## Running Effects

- `effect.run_sync(eff)` - Run synchronously (throws on error)
- `effect.run_async(eff)` - Run asynchronously (throws on error)
- `effect.run_sync_exit(eff)` - Run synchronously (returns Exit)
- `effect.run_async_exit(eff)` - Run asynchronously (returns Exit)

## Combinators

- `effect.map(fn)` - Transform success values
- `effect.flat_map(fn)` - Chain effects together
- `effect.map_error(fn)` - Transform error values
- `effect.tap(fn)` - Perform side effects
- `effect.ignore()` - Discard the success value

See the [tests](https://github.com/pyfect/pyfect/tree/main/tests) for detailed usage examples.
