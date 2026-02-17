"""Tests for option.first_some_of."""

from collections.abc import Generator

from pyfect import option


def test_first_some_of_returns_first_some() -> None:
    result = option.first_some_of(
        [
            option.nothing(),
            option.some(2),
            option.nothing(),
            option.some("hello"),
        ]
    )
    assert option.is_some(result)
    assert result.value == 2  # noqa: PLR2004


def test_first_some_of_all_nothing_returns_nothing() -> None:
    result = option.first_some_of([option.nothing(), option.nothing()])
    assert option.is_nothing(result)


def test_first_some_of_empty_returns_nothing() -> None:
    result = option.first_some_of([])
    assert option.is_nothing(result)


def test_first_some_of_single_some() -> None:
    result = option.first_some_of([option.some(42)])
    assert option.is_some(result)
    assert result.value == 42  # noqa: PLR2004


def test_first_some_of_short_circuits() -> None:
    def generate() -> Generator[option.Option[int]]:
        yield option.nothing()
        yield option.some(1)
        raise RuntimeError("should not be reached")  # noqa: EM101

    result = option.first_some_of(generate())
    assert option.is_some(result)
    assert result.value == 1
