"""Tests for Option core types and constructors."""

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
    try:
        opt.value = 2  # type: ignore[misc]
        msg = "Should have raised"
        raise AssertionError(msg)
    except Exception:
        pass


def test_nothing_is_frozen() -> None:
    n = option.nothing()
    try:
        n.x = 1  # type: ignore[attr-defined]
        msg = "Should have raised"
        raise AssertionError(msg)
    except Exception:
        pass
