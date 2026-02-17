"""Tests for Option core types and constructors."""

from dataclasses import FrozenInstanceError

import pytest

from pyfect import option
from pyfect.option import NOTHING


def test_some_holds_value() -> None:
    opt = option.some(42)
    assert option.is_some(opt)
    assert opt.value == 42  # type checker knows opt is Some[int] here  # noqa: PLR2004


def test_nothing_is_singleton() -> None:
    assert option.nothing() is NOTHING


def test_nothing_is_nothing() -> None:
    assert option.is_nothing(option.nothing())


def test_some_is_not_nothing() -> None:
    assert not option.is_nothing(option.some(1))


def test_nothing_is_not_some() -> None:
    assert not option.is_some(option.nothing())


def test_some_is_frozen() -> None:
    opt = option.some(1)
    with pytest.raises(FrozenInstanceError):
        opt.value = 2  # type: ignore[misc]


def test_nothing_is_immutable() -> None:
    """Nothing is immutable via __slots__, not frozen dataclass."""
    n = option.nothing()
    with pytest.raises(AttributeError):
        n.x = 1  # type: ignore[attr-defined]


def test_nothing_is_hashable() -> None:
    """Nothing can be used in sets and as dict keys."""
    n1 = option.nothing()
    n2 = option.nothing()
    assert hash(n1) == hash(n2)
    # Can be used in a set
    s = {n1, n2}
    assert len(s) == 1


def test_nothing_equality() -> None:
    """Nothing instances are equal to each other."""
    n1 = option.nothing()
    n2 = option.nothing()
    assert n1 == n2
