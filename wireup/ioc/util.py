from __future__ import annotations

import importlib
import typing
import warnings
from inspect import Parameter
from typing import Any, TypeVar

from wireup.errors import WireupError
from wireup.ioc.types import AnnotatedParameter, InjectableType

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


def param_get_annotation(parameter: Parameter, *, globalns: dict[str, Any]) -> AnnotatedParameter | None:
    """Get the annotation injection type from a signature's Parameter.

    Returns the first injectable annotation for an Annotated type or the default value.
    """
    resolved_type: type[Any] | None = ensure_is_type(parameter.annotation, globalns=globalns)

    if resolved_type is Parameter.empty:
        resolved_type = None

    def _get_metadata_from_default_value(parameter: Parameter) -> AnnotatedParameter | None:
        annotation = None if parameter.default is Parameter.empty else _get_injectable_type(parameter.default)

        if annotation:
            warnings.warn(
                "Relying on default values for annotations is deprecated. "
                "Please use Annotated types instead. "
                "E.g.: Annotated[Foo, Inject(...)]. "
                "See: https://maldoinc.github.io/wireup/latest/annotations/",
                DeprecationWarning,
                stacklevel=2,
            )

        return (
            None
            if resolved_type is None and annotation is None
            else AnnotatedParameter(klass=resolved_type, annotation=annotation)
        )

    def _get_metadata_from_annotated_type() -> AnnotatedParameter | None:
        if resolved_type and hasattr(resolved_type, "__metadata__") and hasattr(resolved_type, "__args__"):
            klass = resolved_type.__args__[0]
            annotation = next(_get_injectable_type(ann) for ann in resolved_type.__metadata__)

            return AnnotatedParameter(klass, annotation)

        return None

    if res := _get_metadata_from_annotated_type():
        return res

    return _get_metadata_from_default_value(parameter)


def is_type_autowireable(obj_type: Any) -> bool:
    """Determine if the given type is can be autowired without additional annotations."""
    if obj_type is None or obj_type in {int, float, str, bool, complex, bytes, bytearray, memoryview}:
        return False

    return not (hasattr(obj_type, "__origin__") and obj_type.__origin__ == typing.Union)


def _get_globals(obj: type[Any] | Callable[..., Any]) -> dict[str, Any]:
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
            msg = "Using __future__ annotations in Wireup requires the eval_type_backport package to be installed."
            raise WireupError(msg) from e

    return value
