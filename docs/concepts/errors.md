# Error Handling

!!! warning "Documentation In Progress"
    This section is being developed.

## Errors as Values

In pyfect, errors are not exceptions - they are values that flow through your effect pipeline.

```python
from pyfect import effect

# Run and handle with Exit
result = effect.run_sync_exit(effect.fail("oops"))

match result:
    case effect.Success(value):
        print(f"Got: {value}")
    case effect.Failure(error):
        print(f"Error: {error}")
```

See [test_exit.py](https://github.com/pyfect/pyfect/blob/main/tests/test_exit.py) for examples.
