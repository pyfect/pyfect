# Quick Start

!!! warning "Documentation In Progress"
    This documentation is being developed alongside the library.

## Basic Usage

```python
from pyfect import effect

# Create a simple effect
eff = effect.succeed(42)
result = effect.run_sync(eff)
print(result)  # 42
```

## Composing Effects

```python
from pyfect import effect, pipe

result = pipe(
    effect.succeed(10),
    effect.map(lambda x: x * 2),
    effect.map(lambda x: x + 5),
)

print(effect.run_sync(result))  # 25
```

## More Information

Check the [test files](https://github.com/pyfect/pyfect/tree/main/tests) for comprehensive usage examples.
