"""Tests for option.flat_map."""

from pyfect import option, pipe


def _parse_int(s: str) -> option.Option[int]:
    try:
        return option.some(int(s))
    except ValueError:
        return option.nothing()


def test_flat_map_some_returns_some() -> None:
    result = pipe(option.some("42"), option.flat_map(_parse_int))
    assert option.is_some(result)
    assert result.value == 42  # noqa: PLR2004


def test_flat_map_some_returns_nothing() -> None:
    result = pipe(option.some("xx"), option.flat_map(_parse_int))
    assert option.is_nothing(result)


def test_flat_map_nothing_returns_nothing() -> None:
    result = pipe(option.nothing(), option.flat_map(_parse_int))  # type: ignore[arg-type]
    assert option.is_nothing(result)


def test_flat_map_does_not_double_wrap() -> None:
    result = pipe(option.some(1), option.flat_map(lambda x: option.some(x + 1)))
    assert option.is_some(result)
    assert result.value == 2  # noqa: PLR2004


def test_flat_map_chaining() -> None:
    result = pipe(
        option.some("42"),
        option.flat_map(_parse_int),
        option.flat_map(lambda x: option.some(x * 2)),
    )
    assert option.is_some(result)
    assert result.value == 84  # noqa: PLR2004


def test_flat_map_short_circuits_on_nothing() -> None:
    called = False

    def f(x: int) -> option.Option[int]:
        nonlocal called
        called = True
        return option.some(x)

    pipe(option.nothing(), option.flat_map(f))  # type: ignore[arg-type]
    assert not called
