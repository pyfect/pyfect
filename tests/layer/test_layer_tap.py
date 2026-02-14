"""Tests for layer.tap and layer.tap_error."""

import pytest

from pyfect import effect, layer, pipe


class HTTPServer:
    pass


class StartupError(Exception):
    pass


def test_tap_executes_on_success() -> None:
    """tap callback runs when construction succeeds."""
    log: list[str] = []

    server_layer = pipe(
        layer.sync(HTTPServer, HTTPServer),
        layer.tap(lambda _ctx: effect.sync(lambda: log.append("tapped"))),
    )

    effect.run_sync(layer.launch(server_layer))

    assert log == ["tapped"]


def test_tap_not_executed_on_failure() -> None:
    """tap callback is skipped when construction fails."""
    log: list[str] = []

    failing_layer = pipe(
        layer.effect(HTTPServer, effect.fail(StartupError("boom"))),
        layer.tap(lambda _ctx: effect.sync(lambda: log.append("tapped"))),
    )

    with pytest.raises(StartupError):
        effect.run_sync(layer.launch(failing_layer))

    assert log == []


def test_tap_passes_context_through() -> None:
    """tap does not alter the layer's built context."""
    server_layer = pipe(
        layer.succeed(HTTPServer, HTTPServer()),
        layer.tap(lambda _ctx: effect.succeed(None)),
    )

    eff = pipe(effect.service(HTTPServer), effect.provide(server_layer))
    result = effect.run_sync(eff)

    assert isinstance(result, HTTPServer)


def test_tap_failure_propagates() -> None:
    """If the tap effect fails, the failure propagates."""

    class TapError(Exception):
        pass

    server_layer = pipe(
        layer.sync(HTTPServer, HTTPServer),
        layer.tap(lambda _ctx: effect.fail(TapError("tap failed"))),
    )

    with pytest.raises(TapError, match="tap failed"):
        effect.run_sync(layer.launch(server_layer))


def test_tap_error_executes_on_failure() -> None:
    """tap_error callback runs when construction fails."""
    log: list[str] = []

    failing_layer = pipe(
        layer.effect(HTTPServer, effect.fail(StartupError("port in use"))),
        layer.tap_error(lambda e: effect.sync(lambda: log.append(str(e)))),
    )

    with pytest.raises(StartupError):
        effect.run_sync(layer.launch(failing_layer))

    assert log == ["port in use"]


def test_tap_error_not_executed_on_success() -> None:
    """tap_error callback is skipped when construction succeeds."""
    log: list[str] = []

    server_layer = pipe(
        layer.sync(HTTPServer, HTTPServer),
        layer.tap_error(lambda e: effect.sync(lambda: log.append(str(e)))),
    )

    effect.run_sync(layer.launch(server_layer))

    assert log == []


def test_tap_error_preserves_original_error() -> None:
    """tap_error does not swallow the original error."""
    failing_layer = pipe(
        layer.effect(HTTPServer, effect.fail(StartupError("original"))),
        layer.tap_error(lambda _e: effect.succeed(None)),
    )

    with pytest.raises(StartupError, match="original"):
        effect.run_sync(layer.launch(failing_layer))


def test_tap_and_tap_error_chained() -> None:
    """tap and tap_error can be chained on the same layer."""
    log: list[str] = []

    server_layer = pipe(
        layer.sync(HTTPServer, HTTPServer),
        layer.tap(lambda _ctx: effect.sync(lambda: log.append("success"))),
        layer.tap_error(lambda _e: effect.sync(lambda: log.append("error"))),
    )

    effect.run_sync(layer.launch(server_layer))

    assert log == ["success"]


@pytest.mark.asyncio
async def test_tap_async() -> None:
    """tap works with async execution."""
    log: list[str] = []

    server_layer = pipe(
        layer.sync(HTTPServer, HTTPServer),
        layer.tap(lambda _ctx: effect.sync(lambda: log.append("tapped"))),
    )

    await effect.run_async(layer.launch(server_layer))

    assert log == ["tapped"]


@pytest.mark.asyncio
async def test_tap_error_async() -> None:
    """tap_error works with async execution."""
    log: list[str] = []

    def log_error(e: StartupError) -> effect.Effect[None]:
        return effect.sync(lambda: log.append(str(e)))

    failing_layer = pipe(
        layer.effect(HTTPServer, effect.fail(StartupError("async fail"))),
        layer.tap_error(log_error),
    )

    with pytest.raises(StartupError):
        await effect.run_async(layer.launch(failing_layer))

    assert log == ["async fail"]
