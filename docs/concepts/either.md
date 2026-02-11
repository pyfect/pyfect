# Either

## What is Either?

`Either[R, L]` represents a value that is exclusively one of two things: a `Right[R]` (the success or primary case) or a `Left[L]` (the failure or alternative case).

```python
from pyfect import either

success = either.right(42)       # Right(value=42)
failure = either.left("oops")    # Left(value='oops')
```

Unlike `Effect`, `Either` is not lazy — it is a plain, immutable value you can inspect and pattern match on immediately, with no runtime required.

## Either vs Option vs Exit

| Type | Represents | Failure carries |
|------|-----------|-----------------|
| `Option[A]` | presence or absence | nothing (`Nothing`) |
| `Either[R, L]` | one of two values | a `Left[L]` value |
| `Exit[A, E]` | result of running an effect | a `Failure[E]` value |

Use `Either` when a synchronous computation can fail and the failure is meaningful — you want to carry an error value, not just signal absence. Use `Option` when the only thing that matters is whether a value is present. Use `Exit` when working with the result of running an `Effect`.

## Creating Eithers

```python
from pyfect import either

either.right(42)         # Right(value=42)
either.left("not found") # Left(value='not found')
```

## Guards

Use `is_right` and `is_left` to check which variant you have. Both are proper type narrowing functions:

```python
from pyfect import either

e = either.right(42)

if either.is_right(e):
    print(e.value)  # type checker knows e is Right[int] here
```

Or use Python's native pattern matching directly:

```python
from pyfect.either import Right, Left

match e:
    case Right(value):
        print(f"Got: {value}")
    case Left(value):
        print(f"Error: {value}")
```

## Transforming

### `map`

Transform the `Right` value. `Left` passes through unchanged:

```python
from pyfect import either, pipe

pipe(either.right(1), either.map(lambda x: x + 1))    # Right(value=2)
pipe(either.left("oops"), either.map(lambda x: x + 1)) # Left(value='oops')
```

### `map_left`

Transform the `Left` value. `Right` passes through unchanged:

```python
from pyfect import either, pipe

pipe(either.left("oops"), either.map_left(lambda s: s + "!"))  # Left(value='oops!')
pipe(either.right(1), either.map_left(lambda s: s + "!"))      # Right(value=1)
```

### `map_both`

Transform both sides at once:

```python
from pyfect import either, pipe

pipe(
    either.right(1),
    either.map_both(on_right=lambda n: n + 1, on_left=lambda s: s + "!"),
)
# Right(value=2)
```

## Chaining

### `flat_map`

Chain a computation that itself returns an `Either`. If the input is `Left`, the chain short-circuits:

```python
from pyfect import either, pipe

def parse_int(s: str) -> either.Either[int, str]:
    try:
        return either.right(int(s))
    except ValueError:
        return either.left("not a number")

pipe(either.right("42"), either.flat_map(parse_int))   # Right(value=42)
pipe(either.right("xx"), either.flat_map(parse_int))   # Left(value='not a number')
pipe(either.left("oops"), either.flat_map(parse_int))  # Left(value='oops')
```

Chains short-circuit at the first `Left`:

```python
pipe(
    either.right("42"),
    either.flat_map(parse_int),
    either.flat_map(lambda n: either.right(n * 2) if n > 0 else either.left("non-positive")),
)
# Right(value=84)
```

## Combining

### `zip_with`

Combine two `Either` values with a function. Returns the first `Left` encountered:

```python
from pyfect import either

either.zip_with(either.right("Alice"), either.right(30), lambda name, age: f"{name} is {age}")
# Right(value='Alice is 30')

either.zip_with(either.right("Alice"), either.left("no age"), lambda name, age: f"{name} is {age}")
# Left(value='no age')
```

### `all`

Combine a list or dict of `Either` values. Returns the first `Left` encountered:

```python
from pyfect import either

either.all([either.right(1), either.right(2), either.right(3)])
# Right(value=[1, 2, 3])

either.all([either.right(1), either.left("oops"), either.right(3)])
# Left(value='oops')

either.all({"name": either.right("Alice"), "age": either.right(30)})
# Right(value={'name': 'Alice', 'age': 30})
```

!!! note "Heterogeneous collections"
    Heterogeneous collections work at runtime, but Python's type system cannot unify different `Right` types automatically. Silence the type checker with `# type: ignore` and annotate the result explicitly:

    ```python
    result: either.Either[dict[str, str | int], str] = either.all(  # type: ignore[arg-type]
        {"name": either.right("Alice"), "age": either.right(30)}
    )
    ```

## Interop with Effect

Use `effect.from_either` to convert an `Either` into an `Effect`:

```python
from pyfect import effect, either

def parse_int(s: str) -> either.Either[int, str]:
    try:
        return either.right(int(s))
    except ValueError:
        return either.left("not a number")

match effect.run_sync_exit(effect.from_either(parse_int("42"))):
    case effect.Success(value):
        print(value)   # 42
    case effect.Failure(error):
        print(error)
```

`Right(value)` becomes a successful effect. `Left(value)` becomes a failed effect with that value as the error.
