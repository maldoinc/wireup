from __future__ import annotations

import inspect
import typing
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
    assert typing.get_type_hints(wrapped, include_extras=True) == {
        "name": str,
        "greeter": Injected[Greeter],
        "return": str,
    }


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


@pytest.mark.parametrize("missing", ["args", "kwargs", "both"])
def test_wrap_with_dependencies_requires_varargs_and_kwargs(missing: str) -> None:
    def target(name: str) -> str:
        return name

    def no_args(*, greeter: Injected[Greeter], **kwargs):
        return greeter.greet(target(**kwargs))

    def no_kwargs(*args, greeter: Injected[Greeter]):
        return greeter.greet(target(*args))

    def neither(name: str, greeter: Injected[Greeter]) -> str:
        return greeter.greet(name)

    with pytest.raises(WireupError, match=r"must accept both \*args and \*\*kwargs"):
        wrap_with_dependencies(target)({"args": no_args, "kwargs": no_kwargs, "both": neither}[missing])


def test_wrap_with_dependencies_requires_keyword_only_dependency_parameters() -> None:
    def target(name: str) -> str:
        return name

    with pytest.raises(WireupError, match="must be keyword-only"):

        @wrap_with_dependencies(target)
        def wrapped(greeter: Injected[Greeter], *args, **kwargs):
            _ = greeter
            return target(*args, **kwargs)


def test_wrap_with_dependencies_preserves_variadic_target_parameters() -> None:
    def target(name: str, /, *values: int, suffix: str = "!", **options: str) -> str:
        return f"{name} {values} {suffix} {options}"

    @wrap_with_dependencies(target)
    def wrapped(*args, greeter: Injected[Greeter], **kwargs):
        return greeter.greet(target(*args, **kwargs))

    assert list(inspect.signature(wrapped).parameters) == ["name", "values", "suffix", "greeter", "options"]
    container = wireup.create_sync_container(injectables=[Greeter])
    handler = wireup.inject_from_container(container)(wrapped)
    assert handler("world", 1, 2, suffix="?", extra="value") == "hello world (1, 2) ? {'extra': 'value'}"


@pytest.mark.parametrize("hide_annotated_names", [False, True])
def test_wrap_with_dependencies_resolves_annotations_in_their_own_modules(*, hide_annotated_names: bool) -> None:
    # The same annotation name refers to different dependencies in the two modules.
    target_globals = {"Injected": Injected, "Dependency": RequestContext}
    wrapper_globals = {"Injected": Injected, "Dependency": Greeter, "wrap_with_dependencies": wrap_with_dependencies}
    exec(  # noqa: S102
        "from __future__ import annotations\n"
        "def target(name: str, *, ctx: Injected[Dependency]) -> str:\n"
        "    return name + '/' + ctx.request_id\n",
        target_globals,
    )
    exec(  # noqa: S102
        "from __future__ import annotations\n"
        "def decorate(fn):\n"
        "    @wrap_with_dependencies(fn)\n"
        "    def wrapped(*args, greeter: Injected[Dependency], **kwargs):\n"
        "        return greeter.greet(fn(*args, **kwargs))\n"
        "    return wrapped\n",
        wrapper_globals,
    )
    wrapped = wrapper_globals["decorate"](target_globals["target"])
    hints = typing.get_type_hints(wrapped, include_extras=True)
    assert hints["ctx"] == Injected[RequestContext]
    assert hints["greeter"] == Injected[Greeter]

    container = wireup.create_sync_container(injectables=[RequestContext, Greeter])
    handler = wireup.inject_from_container(container, hide_annotated_names=hide_annotated_names)(wrapped)
    assert handler("world").startswith("hello world/")
    if hide_annotated_names:
        assert list(inspect.signature(handler).parameters) == ["name"]


def test_stacked_decorators_and_target_share_a_scope() -> None:
    container = wireup.create_sync_container(injectables=[RequestContext])
    seen: list[tuple[str, RequestContext]] = []

    def outer(fn):
        @wrap_with_dependencies(fn)
        def wrapped(*args, outer_ctx: Injected[RequestContext], **kwargs):
            seen.append(("outer", outer_ctx))
            return fn(*args, **kwargs)

        return wrapped

    def inner(fn):
        @wrap_with_dependencies(fn)
        def wrapped(*args, inner_ctx: Injected[RequestContext], **kwargs):
            seen.append(("inner", inner_ctx))
            return fn(*args, **kwargs)

        return wrapped

    @wireup.inject_from_container(container)
    @outer
    @inner
    def handler(value: str, ctx: Injected[RequestContext]) -> str:
        seen.append(("target", ctx))
        return value

    assert handler("first") == "first"
    assert handler("second") == "second"
    assert [name for name, _ in seen] == ["outer", "inner", "target"] * 2
    assert seen[0][1] is seen[1][1] is seen[2][1]
    assert seen[3][1] is seen[4][1] is seen[5][1]
    assert seen[0][1] is not seen[3][1]


def test_stacked_decorators_reject_same_name_even_with_same_type() -> None:
    def decorate(fn):
        @wrap_with_dependencies(fn)
        def wrapped(*args, ctx: Injected[RequestContext], **kwargs):
            _ = ctx
            return fn(*args, **kwargs)

        return wrapped

    def target() -> None:
        pass

    with pytest.raises(WireupError, match=r"inner decorator.*Conflicting parameter names: ctx"):
        decorate(decorate(target))


def test_wrap_with_dependencies_preserves_method_binding() -> None:
    container = wireup.create_sync_container(injectables=[Greeter])

    def decorate(fn):
        @wrap_with_dependencies(fn)
        def wrapped(*args, greeter: Injected[Greeter], **kwargs):
            return greeter.greet(fn(*args, **kwargs))

        return wrapped

    class Handler:
        def __init__(self, name: str) -> None:
            self.name = name

        @wireup.inject_from_container(container)
        @decorate
        def greet(self, suffix: str) -> str:
            return self.name + suffix

    assert Handler("world").greet("!") == "hello world!"


async def test_async_wrapper_and_target_share_a_scope() -> None:
    container = wireup.create_async_container(injectables=[RequestContext])
    contexts: list[RequestContext] = []

    def decorate(fn):
        @wrap_with_dependencies(fn)
        async def wrapped(*args, wrapper_ctx: Injected[RequestContext], **kwargs):
            contexts.append(wrapper_ctx)
            return await fn(*args, **kwargs)

        return wrapped

    @wireup.inject_from_container(container)
    @decorate
    async def handler(value: str, ctx: Injected[RequestContext]) -> str:
        assert ctx is contexts[-1]
        return value

    assert inspect.iscoroutinefunction(handler)
    assert await handler("first") == "first"
    assert await handler("second") == "second"
    assert contexts[0] is not contexts[1]


@pytest.mark.parametrize("location", ["target", "wrapper"])
@pytest.mark.parametrize(
    ("annotation", "error_type"),
    [("TypeCheckingOnly", NameError), ("int + str", TypeError), ("invalid (", SyntaxError)],
)
def test_wrap_with_dependencies_reports_annotation_errors(location, annotation, error_type) -> None:
    def target(value):
        return value

    def wrapper(*args, dependency, **kwargs):
        return target(*args, **kwargs), dependency

    fn = target if location == "target" else wrapper
    fn.__annotations__["value" if location == "target" else "dependency"] = annotation

    match = rf"Error evaluating annotations for .*{location}.*{error_type.__name__}"
    with pytest.raises(WireupError, match=match) as exc:
        wrap_with_dependencies(target)(wrapper)

    assert isinstance(exc.value.__cause__, error_type)
    assert "not inside a TYPE_CHECKING block" in str(exc.value)


def test_wrap_with_dependencies_leaves_unmarked_parameters_to_the_caller() -> None:
    def target(**kwargs):
        return kwargs

    @wrap_with_dependencies(target)
    def wrapped(*args, greeter: Injected[Greeter], label: str, verbose: bool = False, **kwargs):
        return greeter.greet(label), verbose, target(*args, **kwargs)

    container = wireup.create_sync_container(injectables=[Greeter])
    handler = wireup.inject_from_container(container)(wrapped)
    assert handler(label="world", other=1) == ("hello world", False, {"other": 1})
    assert handler(label="world", verbose=True) == ("hello world", True, {})
    with pytest.raises(TypeError, match="required keyword-only argument: 'label'"):
        handler()


def test_wrap_with_dependencies_requires_an_injection_site() -> None:
    def target(name: str) -> str:
        return name

    @wrap_with_dependencies(target)
    def wrapped(*args, greeter: Injected[Greeter], **kwargs):
        return greeter.greet(target(*args, **kwargs))

    with pytest.raises(TypeError, match="required keyword-only argument: 'greeter'"):
        wrapped("world")
