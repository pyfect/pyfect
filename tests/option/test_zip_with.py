"""Tests for option.zip_with."""

from pyfect import option


def test_zip_with_both_some() -> None:
    result = option.zip_with(option.some("John"), option.some(25), lambda name, age: (name, age))
    assert option.is_some(result)
    assert result.value == ("John", 25)


def test_zip_with_first_nothing() -> None:
    result = option.zip_with(option.nothing(), option.some(25), lambda a, b: (a, b))
    assert option.is_nothing(result)


def test_zip_with_second_nothing() -> None:
    result = option.zip_with(option.some("John"), option.nothing(), lambda a, b: (a, b))
    assert option.is_nothing(result)


def test_zip_with_both_nothing() -> None:
    result = option.zip_with(option.nothing(), option.nothing(), lambda a, b: (a, b))
    assert option.is_nothing(result)


def test_zip_with_transforms_values() -> None:
    result = option.zip_with(option.some(3), option.some(4), lambda a, b: a * b)
    assert option.is_some(result)
    assert result.value == 12  # noqa: PLR2004


def test_zip_with_narrows_type_when_first_is_nothing() -> None:
    """zip_with should narrow return type to Nothing when first input is Nothing."""
    result: option.Nothing = option.zip_with(option.nothing(), option.some(25), lambda a, b: (a, b))
    assert result is option.NOTHING


def test_zip_with_narrows_type_when_second_is_nothing() -> None:
    """zip_with should narrow return type to Nothing when second input is Nothing."""
    result: option.Nothing = option.zip_with(
        option.some("John"), option.nothing(), lambda a, b: (a, b)
    )
    assert result is option.NOTHING
