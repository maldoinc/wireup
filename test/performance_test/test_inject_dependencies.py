import timeit
import unittest
from dataclasses import dataclass
from typing import Optional

from typing_extensions import Annotated
from wireup import DependencyContainer, Inject, ParameterBag


@dataclass(frozen=True)
class A:
    start: Annotated[int, Inject(param="start")]

    def a(self) -> int:
        return self.start


@dataclass(frozen=True)
class B:
    a: A

    def b(self) -> int:
        return self.a.a() + 1


@dataclass(frozen=True)
class C:
    a: A
    b: B

    def c(self) -> int:
        return self.a.a() * self.b.b()


class UnitTestInject(unittest.TestCase):
    def setUp(self):
        self.container = DependencyContainer(ParameterBag())
        self.container.params.put("start", 4)
        self.container.register(C)
        self.container.register(B)
        self.container.register(A)

        self.container_optimized = DependencyContainer(ParameterBag())
        self.container_optimized.params.put("start", 4)
        self.container_optimized.register(C)
        self.container_optimized.register(B)
        self.container_optimized.register(A)
        self.container_optimized.warmup()

    def test_inject_dependencies(self):
        iterations = 100000

        def native():
            a = A(4)
            b = B(a)
            c = C(a=a, b=b)

            return a.a() + b.b() + c.c()

        def autowired(
            a: A,
            b: B,
            c: C,
            _d: Optional[unittest.TestCase] = None,
            _e: Optional[unittest.TestCase] = None,
            _f: Optional[unittest.TestCase] = None,
            _g: Optional[unittest.TestCase] = None,
        ):
            return c.c() + b.b() + a.a()

        time_baseline = timeit.timeit(native, number=iterations)
        time_wireup_regular = timeit.timeit(self.container.autowire(autowired), number=iterations)
        time_wireup_compiled = timeit.timeit(self.container_optimized.autowire(autowired), number=iterations)

        print(f"{time_baseline=}s")
        print(f"{time_wireup_regular=}s")
        print(f"{time_wireup_compiled=}s")
        print(f"{time_wireup_regular / time_baseline = }x")
        print(f"{time_wireup_compiled / time_baseline = }x")
        print(f"{time_wireup_compiled / time_wireup_regular = }x")
