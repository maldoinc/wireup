from __future__ import annotations

import importlib
import sys
import types
from typing import TYPE_CHECKING, Any

import pytest

from wireup._discovery import _find_objects_in_module

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


def _is_class(obj: Any) -> bool:
    return isinstance(obj, type)


@pytest.fixture
def isolated_imports() -> Iterator[None]:
    before = set(sys.modules)
    yield
    for name in set(sys.modules) - before:
        del sys.modules[name]


def test_module_without_file_attribute_does_not_crash() -> None:
    # PEP 420 namespace packages have no __file__ attribute.
    module = types.ModuleType("wireup_discovery_namespace_package")

    assert _find_objects_in_module(module, predicate=_is_class) == []


def test_file_named_like_init_is_not_treated_as_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, isolated_imports: None
) -> None:
    package = tmp_path / "wireup_notinit_case"
    package.mkdir()
    (package / "not__init__.py").write_text("class First: ...\n")
    (package / "sibling.py").write_text("class Second: ...\n")
    monkeypatch.syspath_prepend(str(tmp_path))

    module = importlib.import_module("wireup_notinit_case.not__init__")

    assert [obj.__name__ for obj in _find_objects_in_module(module, predicate=_is_class)] == ["First"]
    assert "wireup_notinit_case.sibling" not in sys.modules


def test_hidden_entries_are_skipped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, isolated_imports: None) -> None:
    package = tmp_path / "wireup_dotdir_case"
    package.mkdir()
    (package / "__init__.py").write_text("")
    (package / "visible.py").write_text("class Visible: ...\n")
    (package / ".hidden_module.py").write_text("class HiddenModule: ...\n")
    hidden_dir = package / ".hidden"
    hidden_dir.mkdir()
    (hidden_dir / "mod.py").write_text("class Hidden: ...\n")
    monkeypatch.syspath_prepend(str(tmp_path))

    package_module = importlib.import_module("wireup_dotdir_case")

    result = _find_objects_in_module(package_module, predicate=_is_class)

    assert [obj.__name__ for obj in result] == ["Visible"]
    # Only the package and its visible module are imported. Hidden entries are skipped
    # as their names are not valid module names.
    assert sorted(name for name in sys.modules if name.startswith("wireup_dotdir_case")) == [
        "wireup_dotdir_case",
        "wireup_dotdir_case.visible",
    ]


def test_broken_submodule_does_not_abort_discovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, isolated_imports: None
) -> None:
    package = tmp_path / "wireup_broken_case"
    package.mkdir()
    (package / "__init__.py").write_text("")
    (package / "good.py").write_text("class Good: ...\n")
    (package / "broken.py").write_text("import module_that_does_not_exist\n")
    monkeypatch.syspath_prepend(str(tmp_path))

    package_module = importlib.import_module("wireup_broken_case")

    with pytest.warns(UserWarning, match="Failed to import 'wireup_broken_case.broken'"):
        result = _find_objects_in_module(package_module, predicate=_is_class)

    assert [obj.__name__ for obj in result] == ["Good"]
