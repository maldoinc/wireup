from __future__ import annotations

import typing
from inspect import Parameter
from typing import Any

from wireup.ioc.types import AnnotatedParameter, InjectableType


def parameter_get_type_and_annotation(parameter: Parameter) -> AnnotatedParameter:
    """Get the annotation injection type from a signature's Parameter.

    Returns either the first annotation for an Annotated type or the default value.
    """

    def get_injectable_type(metadata: Any) -> InjectableType | None:
        # When using fastapi, the injectable type will be wrapped with Depends.
        # As such, it needs to be unwrapped in order to get the actual metadata
        # Need to be careful here not to unwrap FastAPI dependencies
        # not owned by wireup as they might cause side effects.
        if hasattr(metadata, "dependency") and hasattr(metadata.dependency, "__is_wireup_depends__"):
            metadata = metadata.dependency()

        return metadata if isinstance(metadata, InjectableType) else None

    if hasattr(parameter.annotation, "__metadata__") and hasattr(parameter.annotation, "__args__"):
        klass = parameter.annotation.__args__[0]
        annotation = None

        for ann in parameter.annotation.__metadata__:
            if injectable_type := get_injectable_type(ann):
                annotation = injectable_type
                break
    else:
        klass = None if parameter.annotation is Parameter.empty else parameter.annotation
        annotation = None if parameter.default is Parameter.empty else get_injectable_type(parameter.default)

    return AnnotatedParameter(klass=klass, annotation=annotation)


def is_type_autowireable(obj_type: Any) -> bool:
    """Determine if the given type is can be autowired without additional annotations."""
    if obj_type is None or obj_type in {int, float, str, bool, complex, bytes, bytearray, memoryview}:
        return False

    return not (hasattr(obj_type, "__origin__") and obj_type.__origin__ == typing.Union)
