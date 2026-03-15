from __future__ import annotations

import inspect
import warnings

from wireup.errors import PositionalOnlyParameterError, WireupError
from wireup.ioc.types import AnnotatedParameter, AnyCallable, EmptyContainerInjectionRequest
from wireup.ioc.util import get_globals, param_get_annotation
from wireup.util import stringify_type


def injectable_get_dependencies(factory: AnyCallable) -> dict[str, AnnotatedParameter]:
    dependencies: dict[str, AnnotatedParameter] = {}

    for name, parameter in inspect.signature(factory).parameters.items():
        if parameter.kind in {inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD}:
            continue

        annotated_param = param_get_annotation(parameter, globalns_supplier=lambda: get_globals(factory))

        if not annotated_param:
            if parameter.default is not inspect.Parameter.empty:
                continue

            msg = f"Wireup dependencies must have types. Please add a type to the '{name}' parameter in {factory}."
            raise WireupError(msg)

        if parameter.kind == inspect.Parameter.POSITIONAL_ONLY:
            raise PositionalOnlyParameterError(name, factory)

        if isinstance(annotated_param.annotation, EmptyContainerInjectionRequest):
            warnings.warn(
                f"Redundant Injected[T] or Annotated[T, Inject()] in parameter '{name}' of "
                f"{stringify_type(factory)}. See: "
                "https://maldoinc.github.io/wireup/latest/annotations/",
                stacklevel=2,
            )

        dependencies[name] = annotated_param

    return dependencies
