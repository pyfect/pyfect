# Runtime

!!! warning "Documentation In Progress"
    Runtime documentation is being developed.

## Running Effects

Effects are run using the `effect.run_*` functions:

```python
from pyfect import effect

# Synchronous execution
result = effect.run_sync(my_effect)

# With Exit handling
exit_result = effect.run_sync_exit(my_effect)
```

More documentation coming soon.
