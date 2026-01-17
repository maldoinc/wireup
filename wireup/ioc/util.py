from __future__ import annotations

import functools
import importlib
import inspect
import sys
import typing
from inspect import Parameter
from typing import Any, Sequence, TypeVar, cast

from wireup.errors import WireupError
from wireup.ioc.type_analysis import analyze_type
from wireup.ioc.types import AnnotatedParameter, AnyCallable, InjectableType

T = TypeVar("T")
_eval_type = cast("Callable[..., Any]", typing._eval_type)  # type: ignore[attr-defined]

if typing.TYPE_CHECKING:
    from collections.abc import Callable

    from wireup.ioc.container.base_container import BaseContainer


def _get_injectable_type(metadata: Any) -> InjectableType | None:
    # When using fastapi, the injectable type will be wrapped with Depends.
    # As such, it needs to be unwrapped in order to get the actual metadata
    # Need to be careful here not to unwrap FastAPI dependencies
    # not owned by wireup as they might cause side effects.
    if hasattr(metadata, "dependency") and hasattr(metadata.dependency, "__is_wireup_depends__"):
        metadata = metadata.dependency()

    return metadata if isinstance(metadata, InjectableType) else None


def _get_wireup_annotation(metadata: Sequence[Any]) -> InjectableType | None:
    annotations = list(filter(None, (_get_injectable_type(ann) for ann in metadata)))

    if not annotations:
        return None

    if len(annotations) > 1:
        msg = f"Multiple Wireup annotations used: {annotations}"
        raise WireupError(msg)

    return annotations[0]


def param_get_annotation(
    parameter: Parameter,
    *,
    globalns_supplier: Callable[[], dict[str, Any]],
) -> AnnotatedParameter | None:
    """Get the annotation injection type from a signature's Parameter.

    Returns the first injectable annotation for an Annotated type or the default value.
    Also handles Optional types by marking them as optional in the AnnotatedParameter.
    Supports both Annotated[Optional[T], ...] and Optional[Annotated[T, ...]] patterns.
    """
    resolved_type: type[Any] | None = ensure_is_type(parameter.annotation, globalns_supplier=globalns_supplier)

    if resolved_type is Parameter.empty:
        resolved_type = None

    if not resolved_type:
        return None

    type_analysis = analyze_type(resolved_type)

    return AnnotatedParameter(
        klass=type_analysis.normalized_type,
        annotation=_get_wireup_annotation(type_analysis.annotations),
        has_default_value=parameter.default is not Parameter.empty,
    )


def _type_get_globals(typ: type) -> dict[str, Any]:
    """
    Merge globals from parent classes with the child class's module globals,
    with child class globals taking precedence.
    """
    merged_globals: dict[str, Any] = {}

    for base_class in reversed(typ.__mro__[:-1]):
        base_globals = importlib.import_module(base_class.__module__).__dict__
        merged_globals.update(base_globals)

    return merged_globals


def get_globals(obj: type[Any] | Callable[..., Any]) -> dict[str, Any]:
    """Return the globals for the given object."""
    if isinstance(obj, type):
        return _type_get_globals(obj)

    # Unwrap nested functools.partial to get the underlying function
    while isinstance(obj, functools.partial):
        obj = obj.func

    return obj.__globals__


def _eval_type_native(
    value: typing.ForwardRef,
    globalns: dict[str, Any] | None = None,
) -> Any:
    """Evaluate a ForwardRef using the native typing._eval_type function.

    This function handles version-specific differences in typing._eval_type.
    """
    if sys.version_info >= (3, 14):
        res = _eval_type(value, globalns, None, type_params=())

        return type(None) if res is None else res

    return _eval_type(value, globalns, None)


def ensure_is_type(value: type[T] | str, globalns_supplier: Callable[[], dict[str, Any]]) -> type[T] | None:
    """Ensure the given value represents a type.

    If it is a string it will be evaluated, first trying the native typing._eval_type,
    and falling back to eval_type_backport if needed.

    This approach ensures compatibility with Python 3.14+ where eval_type_backport
    cannot be imported due to ForwardRef subclassing restrictions.
    """
    if not isinstance(value, str):
        return value

    forward_ref = typing.ForwardRef(value)

    try:
        # First, try using the native typing._eval_type then fall back to eval_type_backport.
        # For a more complete solution see the pydantic implementation below.
        # See: https://github.com/pydantic/pydantic/blob/f42171c760d43b9522fde513ae6e209790f7fefb/pydantic/_internal/_typing_extra.py#L485-L512
        return _eval_type_native(forward_ref, globalns=globalns_supplier())  # type:ignore[no-any-return]
    except TypeError as eval_type_error:
        try:
            import eval_type_backport  # noqa: PLC0415
        except ImportError as import_error:
            msg = (
                f"Error evaluating type annotation '{value}'. "
                f"Got: TypeError: {eval_type_error}.\n"
                "Tip: Try using the eval_type_backport package to resolve stringified types.\n"
                "See: https://maldoinc.github.io/wireup/latest/future_annotations/"
            )
            raise WireupError(msg) from import_error

        return eval_type_backport.eval_type_backport(forward_ref, globalns=globalns_supplier(), try_default=False)  # type:ignore[no-any-return]

    except NameError as e:
        msg = (
            f"Error evaluating type annotation '{value}'. Got NameError: {e!s}. "
            "Make sure the type is correctly imported and not inside a TYPE_CHECKING block.\n"
            "See: https://maldoinc.github.io/wireup/latest/future_annotations/"
        )
        raise WireupError(msg) from e




def hide_annotated_names(func: AnyCallable) -> None:
    if hasattr(func, "__wireup_names__"):
        return

    names_to_hide = get_inject_annotated_parameters(func)

    if not names_to_hide:
        return

    orig_sig = inspect.signature(func)
    filtered_params = {name: param for name, param in orig_sig.parameters.items() if param.name not in names_to_hide}
    new_sig = inspect.Signature(parameters=list(filtered_params.values()), return_annotation=orig_sig.return_annotation)
    new_annotations = {
        name: annotation for name, annotation in func.__annotations__.items() if name not in names_to_hide
    }

    func.__wireup_names__ = get_inject_annotated_parameters(func)  # type: ignore[attr-defined]
    func.__signature__ = new_sig  # type: ignore[attr-defined]
    func.__annotations__ = new_annotations

    return


def get_inject_annotated_parameters(target: AnyCallable) -> dict[str, AnnotatedParameter]:
    """Retrieve annotated parameters from a given callable target.

    This function inspects the signature of the provided callable and returns a dictionary
    of parameter names and their corresponding annotated parameters, filtered by those
    that are instances of `InjectableType`.

    Args:
        target (AnyCallable): The callable whose parameters are to be inspected.

    Returns:
        dict[str, AnnotatedParameter]: A dictionary where the keys are parameter names
        and the values are the annotated parameters that are instances of `InjectableType`.

    """
    if hasattr(target, "__wireup_names__"):
        return target.__wireup_names__  # type:ignore[no-any-return]

    return {
        name: param
        for name, parameter in inspect.signature(target).parameters.items()
        if (param := param_get_annotation(parameter, globalns_supplier=lambda: get_globals(target)))
        and isinstance(param.annotation, InjectableType)
    }


def get_valid_injection_annotated_parameters(
    container: BaseContainer, target: AnyCallable
) -> dict[str, AnnotatedParameter]:
    names_to_inject = get_inject_annotated_parameters(target)

    for name, parameter in names_to_inject.items():
        container._registry.assert_dependency_exists(parameter=parameter, target=target, name=name)

    return names_to_inject
