from __future__ import annotations

import importlib
import inspect
import warnings
from pathlib import Path
from types import FunctionType, ModuleType
from typing import TYPE_CHECKING, Any

from wireup._annotations import AbstractDeclaration, InjectableDeclaration

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable


def discover_wireup_registrations(
    injectable_modules: Iterable[ModuleType],
) -> tuple[list[AbstractDeclaration], list[InjectableDeclaration]]:
    abstract_registrations: list[AbstractDeclaration] = []
    injectable_registrations: list[InjectableDeclaration] = []

    def _is_valid_wireup_target(obj: Any) -> bool:
        # Check that the hasattr call is only made on user defined functions and classes.
        # This is so that it avoids interacting with proxies and things such as flask.g when imported.
        # "from flask import g" would cause a hasattr call to g outside of app context.
        return (isinstance(obj, FunctionType) or inspect.isclass(obj)) and hasattr(obj, "__wireup_registration__")

    all_targets: dict[type, None] = {}
    for module in injectable_modules:
        all_targets.update(dict.fromkeys(_find_objects_in_module(module, predicate=_is_valid_wireup_target)))

    for cls in all_targets:
        reg = getattr(cls, "__wireup_registration__", None)

        if isinstance(reg, InjectableDeclaration):
            injectable_registrations.append(reg)
        elif isinstance(reg, AbstractDeclaration):
            abstract_registrations.append(reg)

    return abstract_registrations, injectable_registrations


def _find_objects_in_module(module: ModuleType, predicate: Callable[[Any], bool]) -> list[type]:
    classes: dict[type[Any], None] = {}

    def _module_get_objects(m: ModuleType) -> list[type]:
        # inspect.getmembers sorts by name (via dir()), which reads as an
        # arbitrary reshuffle once "seen order" is the contract this file
        # exists to keep. A module's own __dict__ is insertion-ordered by
        # the interpreter as it executes the file top to bottom, so this
        # is declaration order for free, with no separate tracking needed.
        return [obj for obj in vars(m).values() if predicate(obj)]

    def _find_in_path(path: Path, parent_module_name: str) -> None:
        for file in sorted(path.iterdir()):
            # Hidden entries such as .git or .mypy_cache cannot be imported. Their names
            # are not valid module names and importing them raises ModuleNotFoundError.
            if file.name.startswith(".") or file.name == "__pycache__":
                continue

            full_path = path / file

            if Path.is_dir(full_path):
                sub_module_name = f"{parent_module_name}.{file.name}"
                _find_in_path(full_path, sub_module_name)
            elif file.name.endswith(".py"):
                full_module_name = (
                    parent_module_name if file.name == "__init__.py" else f"{parent_module_name}.{file.name[:-3]}"
                )
                try:
                    sub_module = importlib.import_module(full_module_name)
                except ImportError as e:
                    # A single submodule with a broken import, such as a missing optional
                    # dependency, must not abort discovery of the remaining modules.
                    warnings.warn(
                        f"Failed to import '{full_module_name}' while scanning for Wireup registrations. "
                        f"Skipping it. Original error: {e}",
                        stacklevel=2,
                    )
                    continue
                classes.update(dict.fromkeys(_module_get_objects(sub_module)))

    # PEP 420 namespace packages do not define __file__.
    if f := getattr(module, "__file__", None):
        # Compare the file name as a whole. endswith() would also match files
        # such as not__init__.py and wrongly treat them as packages.
        if Path(f).name == "__init__.py":
            _find_in_path(Path(f).parent, module.__name__)
        else:
            classes.update(dict.fromkeys(_module_get_objects(module)))

    return list(classes)
