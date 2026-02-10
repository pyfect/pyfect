# Option

## What is Option?

`Option[A]` represents a value that may or may not be present. It is either `Some(value)` — containing a value of type `A` — or `Nothing`, representing the absence of a value.

```python
from pyfect import option

present = option.some(42)    # Some(value=42)
absent  = option.nothing()   # Nothing()
```

This is a structured alternative to using `None` directly. The key difference is that `Option[A]` is explicit in the type signature — a function returning `Option[str]` clearly communicates that the value may be absent, whereas `str | None` relies on the caller remembering to check.

Tony Hoare, who invented the null reference, famously called it his ["Billion Dollar Mistake"](https://www.infoq.com/presentations/Null-References-The-Billion-Dollar-Mistake-Tony-Hoare/) — null references are so easy to forget to handle that they have caused incalculable bugs and crashes over the decades. `Option` is the structured answer to that problem.

## Creating Options

### From a known value or absence

```python
from pyfect import option

some_value  = option.some("hello")
no_value    = option.nothing()
```

`nothing()` always returns the same singleton `NOTHING` — no allocation on repeated calls.

### From a nullable value

`from_optional` converts Python's `A | None` into an `Option[A]`:

```python
from pyfect import option

option.from_optional("hello")  # Some(value='hello')
option.from_optional(None)     # Nothing()
option.from_optional(0)        # Some(value=0)  — falsy values are preserved
option.from_optional("")       # Some(value='')  — empty string is not None
```

Note that `from_optional` checks for `None` specifically — not falsiness. `0`, `""`, and `[]` all become `Some`.

### From a predicate

`lift_predicate` turns a predicate function into a constructor:

```python
from pyfect import option

parse_positive = option.lift_predicate(lambda n: n > 0)

parse_positive(42)   # Some(value=42)
parse_positive(-1)   # Nothing()
```

## Guards

Use `is_some` and `is_nothing` to check which variant you have. Both are proper type narrowing functions — after the check, the type checker knows exactly what you're working with:

```python
from pyfect import option

opt = option.some(42)

if option.is_some(opt):
    print(opt.value)  # type checker knows opt is Some[int] here
```

Or use Python's native pattern matching directly:

```python
from pyfect.option import Some, Nothing

match opt:
    case Some(value):
        print(f"Got: {value}")
    case Nothing():
        print("Nothing here")
```

## Transforming Options

### `map`

Transform the value inside a `Some`. `Nothing` passes through unchanged:

```python
from pyfect import option, pipe

pipe(option.some(21), option.map(lambda x: x * 2))   # Some(value=42)
pipe(option.nothing(), option.map(lambda x: x * 2))  # Nothing()
```

### `flat_map`

Chain a computation that itself may return `Nothing`:

```python
from pyfect import option, pipe

def find_config(key: str) -> option.Option[str]:
    config = {"host": "localhost"}
    return option.from_optional(config.get(key))

def parse_port(s: str) -> option.Option[int]:
    try:
        return option.some(int(s))
    except ValueError:
        return option.nothing()

result = pipe(
    find_config("port"),
    option.flat_map(parse_port),
)
# Nothing() — "port" key not found
```

### `filter`

Keep the value only if it satisfies a predicate:

```python
from pyfect import option, pipe

pipe(option.some(42), option.filter(lambda x: x > 0))   # Some(value=42)
pipe(option.some(-1), option.filter(lambda x: x > 0))   # Nothing()
```

## Extracting values

### `get_or_else`

Provide a default value when `Nothing`:

```python
from pyfect import option, pipe

pipe(option.some(42), option.get_or_else(lambda: 0))   # 42
pipe(option.nothing(), option.get_or_else(lambda: 0))  # 0
```

The default is a thunk — it is only evaluated when the option is `Nothing`.

### `get_or_none`

Convert back to Python's `A | None`:

```python
from pyfect import option, pipe

pipe(option.some(42), option.get_or_none)   # 42
pipe(option.nothing(), option.get_or_none)  # None
```

### `get_or_raise`

Raise a `ValueError` if `Nothing`:

```python
from pyfect import option, pipe

pipe(option.some(42), option.get_or_raise)   # 42
pipe(option.nothing(), option.get_or_raise)  # raises ValueError
```

## Fallback

### `or_else`

Try an alternative when `Nothing`:

```python
from pyfect import option, pipe

pipe(option.some(42), option.or_else(lambda: option.some(0)))   # Some(value=42)
pipe(option.nothing(), option.or_else(lambda: option.some(0)))  # Some(value=0)
```

### `first_some_of`

Return the first `Some` from an iterable:

```python
from pyfect import option

option.first_some_of([option.nothing(), option.some(2), option.some(3)])  # Some(value=2)
option.first_some_of([option.nothing(), option.nothing()])                 # Nothing()
```

## Combining Options

### `zip_with`

Combine two `Option` values with a function. If either is `Nothing`, the result is `Nothing`:

```python
from pyfect import option

option.zip_with(option.some("Alice"), option.some(30), lambda name, age: f"{name} is {age}")
# Some(value='Alice is 30')

option.zip_with(option.some("Alice"), option.nothing(), lambda name, age: f"{name} is {age}")
# Nothing()
```

### `all`

Combine a list or dict of Options. Returns `Nothing` if any element is `Nothing`:

```python
from pyfect import option

option.all([option.some(1), option.some(2), option.some(3)])  # Some(value=[1, 2, 3])
option.all([option.some(1), option.nothing(), option.some(3)])  # Nothing()

option.all({"a": option.some(1), "b": option.some(2)})  # Some(value={'a': 1, 'b': 2})
```

!!! note "Heterogeneous collections"
    Heterogeneous collections work at runtime, but Python's type system cannot unify different value types into a single `Option[A]`. Silence the type checker with `# type: ignore` and annotate the result explicitly:

    ```python
    result: option.Option[dict[str, str | int]] = option.all(  # type: ignore[arg-type]
        {"name": option.some("Alice"), "age": option.some(30)}
    )
    ```

## Interop with Effect

Use `effect.from_option` to convert an `Option` into an `Effect`:

```python
from pyfect import effect, option, pipe

def find_user(user_id: int) -> option.Option[str]:
    users = {1: "Alice", 2: "Bob"}
    return option.from_optional(users.get(user_id))

result = pipe(
    find_user(99),
    effect.from_option(lambda: "User 99 not found"),
)

match effect.run_sync_exit(result):
    case effect.Success(value):
        print(value)
    case effect.Failure(error):
        print(error)  # User 99 not found
```

`Some(value)` becomes a successful effect. `Nothing` becomes a failed effect using the provided error thunk.
