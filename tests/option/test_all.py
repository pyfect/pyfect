"""Tests for option.all."""

from pyfect import option


def test_all_list_all_some() -> None:
    result = option.all([option.some(1), option.some(2), option.some(3)])
    assert option.is_some(result)
    assert result.value == [1, 2, 3]


def test_all_list_with_nothing() -> None:
    result = option.all([option.some(1), option.nothing(), option.some(3)])
    assert option.is_nothing(result)


def test_all_list_empty() -> None:
    result = option.all([])
    assert option.is_some(result)
    assert result.value == []


def test_all_dict_all_some() -> None:
    result = option.all({"a": option.some(1), "b": option.some(2), "c": option.some(3)})
    assert option.is_some(result)
    assert result.value == {"a": 1, "b": 2, "c": 3}


def test_all_dict_with_nothing() -> None:
    result = option.all({"a": option.some(1), "b": option.nothing()})
    assert option.is_nothing(result)


def test_all_dict_empty() -> None:
    result = option.all({})
    assert option.is_some(result)
    assert result.value == {}
