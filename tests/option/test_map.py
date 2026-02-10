"""Tests for option.map."""

from pyfect import option, pipe


def test_map_some_transforms_value() -> None:
    result = pipe(option.some(42), option.map(lambda x: x * 2))
    assert option.is_some(result)
    assert result.value == 84  # noqa: PLR2004


def test_map_nothing_returns_nothing() -> None:
    result = pipe(option.nothing(), option.map(lambda x: x * 2))  # type: ignore
    assert option.is_nothing(result)


def test_map_preserves_singleton() -> None:
    result = pipe(option.nothing(), option.map(lambda x: x))
    assert result is option.NOTHING


def test_map_chaining() -> None:
    result = pipe(
        option.some(1),
        option.map(lambda x: x + 1),
        option.map(lambda x: x * 10),
    )
    assert option.is_some(result)
    assert result.value == 20  # noqa: PLR2004


def test_map_type_change() -> None:
    result = pipe(option.some(42), option.map(str))
    assert option.is_some(result)
    assert result.value == "42"
