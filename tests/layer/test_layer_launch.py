"""Tests for layer.launch."""

import pytest

from pyfect import effect, layer, pipe


class HTTPServer:
    pass


class Worker:
    pass


def test_launch_runs_construction_side_effect() -> None:
    """launch runs the layer's construction effect."""
    log: list[str] = []

    def start() -> HTTPServer:
        log.append("started")
        return HTTPServer()

    server_layer = layer.effect(HTTPServer, effect.sync(start))

    effect.run_sync(layer.launch(server_layer))

    assert log == ["started"]


def test_launch_returns_none() -> None:
    """launch discards the built context and returns None."""
    server_layer = layer.succeed(HTTPServer, HTTPServer())

    result = effect.run_sync(layer.launch(server_layer))

    assert result is None


def test_launch_propagates_construction_failure() -> None:
    """launch propagates errors from the construction effect."""

    class StartupError(Exception):
        pass

    failing_layer = layer.effect(
        HTTPServer,
        effect.fail(StartupError("port already in use")),
    )

    with pytest.raises(StartupError, match="port already in use"):
        effect.run_sync(layer.launch(failing_layer))


def test_launch_with_provided_dependencies() -> None:
    """launch works on a layer that has had its dependencies satisfied."""
    log: list[str] = []

    class Config:
        def __init__(self, port: int) -> None:
            self.port = port

    def start(c: Config) -> HTTPServer:
        log.append(f"listening on {c.port}")
        return HTTPServer()

    server_layer = pipe(
        layer.effect(
            HTTPServer,
            pipe(effect.service(Config), effect.map_(start)),
        ),
        layer.provide(layer.succeed(Config, Config(8080))),
    )

    effect.run_sync(layer.launch(server_layer))

    assert log == ["listening on 8080"]


@pytest.mark.asyncio
async def test_launch_async() -> None:
    """launch works with async execution."""
    log: list[str] = []

    def start() -> HTTPServer:
        log.append("started")
        return HTTPServer()

    server_layer = layer.effect(HTTPServer, effect.sync(start))

    await effect.run_async(layer.launch(server_layer))

    assert log == ["started"]
