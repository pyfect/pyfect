"""Tests for option.lift_predicate."""

from pyfect import option


def test_lift_predicate_passes_returns_some() -> None:
    def is_positive(n: int) -> bool:
        return n > 0

    parse_positive = option.lift_predicate(is_positive)
    result = parse_positive(42)
    assert option.is_some(result)
    assert result.value == 42  # noqa: PLR2004


def test_lift_predicate_fails_returns_nothing() -> None:
    def is_positive(n: int) -> bool:
        return n > 0

    parse_positive = option.lift_predicate(is_positive)
    result = parse_positive(-1)
    assert option.is_nothing(result)


def test_lift_predicate_equivalent_to_filter_some() -> None:
    def predicate(n: int) -> bool:
        return n > 0

    value = 42

    from_lift = option.lift_predicate(predicate)(value)
    from_filter = option.filter_(predicate)(option.some(value))

    assert from_lift == from_filter


def test_lift_predicate_returns_singleton_on_failure() -> None:
    def always_false(_: int) -> bool:
        return False

    result = option.lift_predicate(always_false)(42)
    assert result is option.NOTHING
