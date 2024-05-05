from __future__ import annotations

import typing
import warnings
from inspect import Parameter
from typing import Any

from wireup.ioc.types import AnnotatedParameter, InjectableType


def _get_injectable_type(metadata: Any) -> InjectableType | None:
    # When using fastapi, the injectable type will be wrapped with Depends.
    # As such, it needs to be unwrapped in order to get the actual metadata
    # Need to be careful here not to unwrap FastAPI dependencies
    # not owned by wireup as they might cause side effects.
    if hasattr(metadata, "dependency") and hasattr(metadata.dependency, "__is_wireup_depends__"):
        metadata = metadata.dependency()

    return metadata if isinstance(metadata, InjectableType) else None


def _find_first_injectable_annotation(parameter: Parameter) -> InjectableType | None:
    return next(_get_injectable_type(ann) for ann in parameter.annotation.__metadata__)


def _get_metadata_from_annotated_type(parameter: Parameter) -> AnnotatedParameter | None:
    if hasattr(parameter.annotation, "__metadata__") and hasattr(parameter.annotation, "__args__"):
        klass = parameter.annotation.__args__[0]
        annotation = _find_first_injectable_annotation(parameter)

        return AnnotatedParameter(klass, annotation)

    return None


def _get_metadata_from_default_value(parameter: Parameter) -> AnnotatedParameter | None:
    warnings.warn(
        "Using default values to annotate parameters for injection is deprecated. "
        "Use annotated types. E.g.: Annotated[str, Wire(...)]",
        stacklevel=2,
    )
    klass = None if parameter.annotation is Parameter.empty else parameter.annotation
    annotation = None if parameter.default is Parameter.empty else _get_injectable_type(parameter.default)

    return None if klass is None and annotation is None else AnnotatedParameter(klass=klass, annotation=annotation)


def param_get_annotation(parameter: Parameter) -> AnnotatedParameter | None:
    """Get the annotation injection type from a signature's Parameter.

    Returns the first injectable annotation for an Annotated type or the default value.
    """
    if res := _get_metadata_from_annotated_type(parameter):
        return res

    return _get_metadata_from_default_value(parameter)


def is_type_autowireable(obj_type: Any) -> bool:
    """Determine if the given type is can be autowired without additional annotations."""
    if obj_type is None or obj_type in {int, float, str, bool, complex, bytes, bytearray, memoryview}:
        return False

    return not (hasattr(obj_type, "__origin__") and obj_type.__origin__ == typing.Union)
