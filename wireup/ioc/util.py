from __future__ import annotations

import importlib
import typing
from inspect import Parameter
from typing import Any, Sequence, TypeVar

from wireup.errors import WireupError
from wireup.ioc.types import AnnotatedParameter, AnyCallable, InjectableType

if typing.TYPE_CHECKING:
    from collections.abc import Callable


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
    """
    resolved_type: type[Any] | None = ensure_is_type(parameter.annotation, globalns=globalns)

    if resolved_type is Parameter.empty:
        resolved_type = None

    if resolved_type and hasattr(resolved_type, "__metadata__") and hasattr(resolved_type, "__args__"):
        klass = resolved_type.__args__[0]
        annotation = _get_wireup_annotation(resolved_type.__metadata__)

        return AnnotatedParameter(klass, annotation)

    return None if not resolved_type else AnnotatedParameter(klass=resolved_type)


def get_globals(obj: type[Any] | Callable[..., Any]) -> dict[str, Any]:
    """Return the globals for the given object."""
    if isinstance(obj, type):
        return importlib.import_module(obj.__module__).__dict__

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


def stringify_type(target: type | AnyCallable) -> str:
    return f"{type(target).__name__.capitalize()} {target.__module__}.{target.__name__}"
