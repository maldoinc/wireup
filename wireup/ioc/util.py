from __future__ import annotations

import functools
import importlib
import inspect
import types
import typing
from inspect import Parameter
from typing import Any, Sequence, TypeVar

from wireup.errors import WireupError
from wireup.ioc.types import AnnotatedParameter, AnyCallable, InjectableType

_OPTIONAL_UNION_ARG_COUNT = 2

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


def param_get_annotation(parameter: Parameter, *, globalns: dict[str, Any]) -> AnnotatedParameter | None:
    """Get the annotation injection type from a signature's Parameter.

    Returns the first injectable annotation for an Annotated type or the default value.
    Also handles Optional types by marking them as optional in the AnnotatedParameter.
    Supports both Annotated[Optional[T], ...] and Optional[Annotated[T, ...]] patterns.
    """
    resolved_type: type[Any] | None = ensure_is_type(parameter.annotation, globalns=globalns)

    if resolved_type is Parameter.empty:
        resolved_type = None

    if not resolved_type:
        return None

    annotation = None
    inner_type = resolved_type

    # Handle Annotated[Optional[T], ...] pattern
    if hasattr(resolved_type, "__metadata__") and hasattr(resolved_type, "__args__"):
        annotation = _get_wireup_annotation(resolved_type.__metadata__)
        inner_type = resolved_type.__args__[0]
        unwrapped_type = unwrap_optional_type(inner_type)
        inner_type = unwrapped_type
    else:
        # Handle Optional[T] or Optional[Annotated[T, ...]] pattern
        unwrapped_type = unwrap_optional_type(resolved_type)
        inner_type = unwrapped_type
        if hasattr(inner_type, "__metadata__") and hasattr(inner_type, "__args__"):
            annotation = _get_wireup_annotation(inner_type.__metadata__)
            inner_type = inner_type.__args__[0]

    return AnnotatedParameter(klass=inner_type, annotation=annotation)


def get_globals(obj: type[Any] | Callable[..., Any]) -> dict[str, Any]:
    """Return the globals for the given object."""
    if isinstance(obj, type):
        return importlib.import_module(obj.__module__).__dict__

    # Unwrap nested functools.partial to get the underlying function
    while isinstance(obj, functools.partial):
        obj = obj.func

    return obj.__globals__


T = TypeVar("T")


def ensure_is_type(value: type[T] | str, globalns: dict[str, Any] | None = None) -> type[T] | None:
    """Ensure the given value represents a type.

    If it is a string it will be evaluated using eval_type_backport.
    """
    if isinstance(value, str):
        try:
            import eval_type_backport

            return eval_type_backport.eval_type_backport(  # type:ignore[no-any-return]
                eval_type_backport.ForwardRef(value), globalns=globalns, try_default=False
            )
        except NameError:
            return None
        except ImportError as e:
            msg = (
                "Using __future__ annotations in Wireup requires the eval_type_backport package to be installed. "
                "See: https://maldoinc.github.io/wireup/latest/future_annotations/"
            )
            raise WireupError(msg) from e

    return value


def unwrap_optional_type(type_: Any) -> Any:
    """If the given type is Optional[T], returns T. Otherwise returns type_."""
    valid_origins = [typing.Union]

    # types.UnionType requires py310+
    if union_type := getattr(types, "UnionType", None):
        valid_origins.append(union_type)

    origin = typing.get_origin(type_) or type_
    if origin in valid_origins:
        args = typing.get_args(type_)
        if len(args) == _OPTIONAL_UNION_ARG_COUNT and type(None) in args:
            return next(arg for arg in args if arg is not type(None))

    return type_


def stringify_type(target: type | AnyCallable) -> str:
    return f"{type(target).__name__.capitalize()} {target.__module__}.{target.__name__}"


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
        if (param := param_get_annotation(parameter, globalns=get_globals(target)))
        and isinstance(param.annotation, InjectableType)
    }


def get_valid_injection_annotated_parameters(
    container: BaseContainer, target: AnyCallable
) -> dict[str, AnnotatedParameter]:
    names_to_inject = get_inject_annotated_parameters(target)

    for name, parameter in names_to_inject.items():
        container._registry.assert_dependency_exists(parameter=parameter, target=target, name=name)

    return names_to_inject
