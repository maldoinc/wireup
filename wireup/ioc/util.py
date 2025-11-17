from __future__ import annotations

import importlib
import sys
import types
import typing
from inspect import Parameter
from typing import Any, Sequence, TypeVar

from wireup.errors import WireupError
from wireup.ioc.types import AnnotatedParameter, AnyCallable, InjectableType

_OPTIONAL_UNION_ARG_COUNT = 2

if typing.TYPE_CHECKING:
    from collections.abc import Callable

    _EvalTypeFn = Callable[..., Any]
else:
    _EvalTypeFn = Any


# Runtime: fetch typing._eval_type safely
_eval_type: _EvalTypeFn | None = getattr(typing, "_eval_type", None)


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

    return obj.__globals__


T = TypeVar("T")


def _eval_type_native(
    value: typing.ForwardRef,
    globalns: dict[str, Any] | None = None,
    localns: dict[str, Any] | None = None,
) -> Any:
    """Evaluate a ForwardRef using the native typing._eval_type function.

    This function handles version-specific differences in the _eval_type signature.
    """

    if _eval_type is None:
        msg = "typing._eval_type is not available in this Python version."
        raise RuntimeError(msg)

    if sys.version_info >= (3, 12):
        return _eval_type(value, globalns, localns, None)
    return _eval_type(value, globalns, localns)


def _is_backport_fixable_error(e: TypeError) -> bool:
    """Check if the TypeError can be fixed by eval_type_backport."""
    msg = str(e)
    # This error occurs in Python < 3.10 when using the new union syntax (X | Y)
    return sys.version_info < (3, 10) and msg.startswith("unsupported operand type(s) for |: ")


def ensure_is_type(value: type[T] | str, globalns: dict[str, Any] | None = None) -> type[T] | None:
    """Ensure the given value represents a type.

    If it is a string it will be evaluated, first trying the native typing._eval_type,
    and falling back to eval_type_backport if needed.

    This approach ensures compatibility with Python 3.14+ where eval_type_backport
    cannot be imported due to ForwardRef subclassing restrictions.
    """
    if isinstance(value, str):
        # Convert string to ForwardRef
        forward_ref = typing.ForwardRef(value)

        try:
            # First, try using the native typing._eval_type
            return _eval_type_native(forward_ref, globalns=globalns)  # type:ignore[no-any-return]
        except TypeError as e:
            # Check if this is an error that eval_type_backport can fix
            if not (isinstance(forward_ref, typing.ForwardRef) and _is_backport_fixable_error(e)):
                # If it's not fixable by the backport, re-raise
                raise

            # Try to import and use eval_type_backport as a fallback
            try:
                import eval_type_backport

                return eval_type_backport.eval_type_backport(forward_ref, globalns=globalns, try_default=False)  # type:ignore[no-any-return]
            except ImportError as import_error:
                msg = (
                    "Using __future__ annotations in Wireup requires the eval_type_backport package to be installed. "
                    "See: https://maldoinc.github.io/wireup/latest/future_annotations/"
                )
                raise WireupError(msg) from import_error
        except NameError:
            # The name in the forward reference doesn't exist
            return None

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
