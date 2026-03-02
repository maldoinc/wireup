"""
Shared service classes for DI framework benchmarks.

This module contains the common service layer used across all DI framework setups
to avoid code duplication.
"""

import os
from dataclasses import dataclass
from threading import Lock
from typing import AsyncIterator, Dict, Iterator, Tuple

_COUNTERS: Dict[str, int] = {}
_COUNTER_LOCK = Lock()
_ASSERT_ENABLED = os.getenv("BENCH_ASSERT") == "1"


def _inc(key: str, amount: int = 1) -> None:
    if not _ASSERT_ENABLED:
        return
    with _COUNTER_LOCK:
        _COUNTERS[key] = _COUNTERS.get(key, 0) + amount


def record_request(test_name: str) -> None:
    _inc(f"request.{test_name}")


def record_created(name: str) -> None:
    _inc(f"create.{name}")


def record_enter(name: str) -> None:
    _inc(f"enter.{name}")


def record_exit(name: str) -> None:
    _inc(f"exit.{name}")


def get_counters() -> Dict[str, int]:
    if not _ASSERT_ENABLED:
        return {}
    with _COUNTER_LOCK:
        return dict(_COUNTERS)


def reset_counters() -> None:
    if not _ASSERT_ENABLED:
        return
    with _COUNTER_LOCK:
        _COUNTERS.clear()


def _expected_counts(requests_singleton: int, requests_scoped: int) -> Dict[str, int]:
    expected: Dict[str, int] = {}
    singleton_expected = 1 if requests_singleton > 0 else 0
    for name in ("Settings", "A", "B"):
        expected[f"create.{name}"] = singleton_expected
    for name in ("C", "D", "E", "F", "G", "H", "I"):
        expected[f"create.{name}"] = requests_scoped
    expected["enter.H"] = requests_scoped
    expected["exit.H"] = requests_scoped
    expected["enter.I"] = requests_scoped
    expected["exit.I"] = requests_scoped
    expected["request.singleton"] = requests_singleton
    expected["request.scoped"] = requests_scoped
    return expected


def assert_workload(
    overrides: Dict[str, int] | None = None,
) -> Tuple[bool, Dict[str, int], Dict[str, int], Dict[str, int]]:
    if not _ASSERT_ENABLED:
        return True, {}, {}, {}
    counters = get_counters()
    requests_singleton = counters.get("request.singleton", 0)
    requests_scoped = counters.get("request.scoped", 0)
    expected = _expected_counts(requests_singleton, requests_scoped)
    if overrides:
        expected.update(overrides)
    mismatches: Dict[str, int] = {}
    singleton_create_keys = {"create.Settings", "create.A", "create.B"}
    for key, expected_value in expected.items():
        actual_value = counters.get(key, 0)
        # Some benchmark setups eagerly instantiate singleton services at startup
        # (outside request handling). Treat +/-1 drift on singleton creation as
        # acceptable so we still catch per-request singleton creation regressions.
        if key in singleton_create_keys and abs(actual_value - expected_value) <= 1:
            continue
        if actual_value != expected_value:
            mismatches[key] = actual_value
    return not mismatches, expected, counters, mismatches


class Settings:
    """Application settings."""

    start: int = 10

    def __init__(self, start: int = 10) -> None:
        record_created("Settings")
        self.start = start


@dataclass(frozen=True)
class A:
    """Service A that depends on settings."""

    start: int

    def __post_init__(self) -> None:
        record_created("A")


@dataclass(frozen=True)
class B:
    """Service B that depends on A."""

    a: A

    def __post_init__(self) -> None:
        record_created("B")


@dataclass(frozen=True)
class C:
    """Service C, root of the scoped graph."""

    def __post_init__(self) -> None:
        record_created("C")


@dataclass(frozen=True)
class D:
    """Service D that depends on C."""

    c: C

    def __post_init__(self) -> None:
        record_created("D")


@dataclass(frozen=True)
class E:
    """Service E that depends on C and D."""

    c: C
    d: D

    def __post_init__(self) -> None:
        record_created("E")


@dataclass(frozen=True)
class F:
    """Service F that depends on C, D, and E."""

    c: C
    d: D
    e: E

    def __post_init__(self) -> None:
        record_created("F")


@dataclass(frozen=True)
class G:
    """Service G that depends on C, D, E, and F."""

    c: C
    d: D
    e: E
    f: F

    def __post_init__(self) -> None:
        record_created("G")


def make_a(settings: Settings) -> A:
    """Factory function to create service A from settings."""
    return A(settings.start)


@dataclass(frozen=True)
class H:
    """Service H that depends on C and D."""

    c: C
    d: D

    def __post_init__(self) -> None:
        record_created("H")


def make_h(c: C, d: D) -> Iterator[H]:
    record_enter("H")
    try:
        yield H(c, d)
    finally:
        record_exit("H")


@dataclass(frozen=True)
class I:
    """Service I that depends on E and F."""

    e: E
    f: F

    def __post_init__(self) -> None:
        record_created("I")


async def make_i(e: E, f: F) -> AsyncIterator[I]:
    record_enter("I")
    try:
        yield I(e, f)
    finally:
        record_exit("I")
