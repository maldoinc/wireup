from __future__ import annotations

import uuid

import pytest
import wireup
from wireup import Injected, injectable, wrap_with_dependencies
from wireup.errors import WireupError


@injectable
class Greeter:
    def greet(self, name: str) -> str:
        return f"hello {name}"


@injectable(lifetime="scoped")
class RequestContext:
    def __init__(self) -> None:
        self.request_id = uuid.uuid4().hex


def test_wrap_with_dependencies_injects_wrapper_dependencies() -> None:
    container = wireup.create_sync_container(injectables=[Greeter])

    def add_greeting(fn):
        @wrap_with_dependencies(fn)
        def wrapped(*args, greeter: Injected[Greeter], **kwargs):
            return f"{greeter.greet(args[0])} / {fn(*args, **kwargs)}"

        return wrapped

    @wireup.inject_from_container(container)
    @add_greeting
    def handler(name: str) -> str:
        return f"handled {name}"

    assert handler("world") == "hello world / handled world"


def test_wrap_with_dependencies_can_trigger_scope_creation() -> None:
    container = wireup.create_sync_container(injectables=[RequestContext])
    seen_ids: list[str] = []

    def capture_request_id(fn):
        @wrap_with_dependencies(fn)
        def wrapped(*args, ctx: Injected[RequestContext], **kwargs):
            seen_ids.append(ctx.request_id)
            return fn(*args, **kwargs)

        return wrapped

    @wireup.inject_from_container(container)
    @capture_request_id
    def handler(value: str) -> str:
        return value

    assert handler("a") == "a"
    assert handler("b") == "b"
    assert len(seen_ids) == 2
    assert seen_ids[0] != seen_ids[1]


def test_wrap_with_dependencies_preserves_wraps_metadata() -> None:
    def target(name: str) -> str:
        """target doc"""
        return name

    def decorator(fn):
        @wrap_with_dependencies(fn)
        def wrapped(*args, greeter: Injected[Greeter], **kwargs):
            _ = greeter
            return fn(*args, **kwargs)

        return wrapped

    wrapped = decorator(target)

    assert wrapped.__name__ == "target"
    assert wrapped.__doc__ == "target doc"
    assert wrapped.__wrapped__ is target


def test_wrap_with_dependencies_rejects_parameter_name_collisions() -> None:
    def decorator(fn):
        with pytest.raises(WireupError, match="Conflicting parameter names: ctx"):

            @wrap_with_dependencies(fn)
            def wrapped(*args, ctx: Injected[RequestContext], **kwargs):
                _ = ctx
                return fn(*args, **kwargs)

        return fn

    @decorator
    def handler(ctx: str) -> str:
        return ctx


def test_wrap_with_dependencies_requires_varargs_and_kwargs() -> None:
    def target(name: str) -> str:
        return name

    with pytest.raises(WireupError, match=r"must accept both \*args and \*\*kwargs"):

        @wrap_with_dependencies(target)
        def wrapped(name: str, greeter: Injected[Greeter]) -> str:
            _ = greeter
            return name


def test_wrap_with_dependencies_requires_keyword_only_dependency_parameters() -> None:
    def target(name: str) -> str:
        return name

    with pytest.raises(WireupError, match="must be keyword-only"):

        @wrap_with_dependencies(target)
        def wrapped(greeter: Injected[Greeter], *args, **kwargs):
            _ = greeter
            return target(*args, **kwargs)
