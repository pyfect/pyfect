"""Tests for option.from_optional."""

from pyfect import option, pipe


def test_from_optional_value_returns_some() -> None:
    result = option.from_optional(42)
    assert option.is_some(result)
    assert result.value == 42  # noqa: PLR2004


def test_from_optional_none_returns_nothing() -> None:
    result = option.from_optional(None)
    assert option.is_nothing(result)


def test_from_optional_none_returns_singleton() -> None:
    assert option.from_optional(None) is option.NOTHING


def test_from_optional_round_trips_with_get_or_none() -> None:
    assert pipe(option.from_optional(42), option.get_or_none) == 42  # noqa: PLR2004
    assert pipe(option.from_optional(None), option.get_or_none) is None


def test_from_optional_zero_is_some() -> None:
    result = option.from_optional(0)
    assert option.is_some(result)


def test_from_optional_empty_string_is_some() -> None:
    result = option.from_optional("")
    assert option.is_some(result)
