import timeit
import unittest
from dataclasses import dataclass

from typing_extensions import Annotated

from wireup import ParameterBag, DependencyContainer, Wire


@dataclass(frozen=True)
class A:
    start: Annotated[int, Wire(param="start")]

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
        self.container.register(A)
        self.container.register(B)
        self.container.register(C)

    def test_inject_dependencies(self):
        iterations = 10000

        def native():
            a = A(4)
            b = B(a)
            c = C(a=a, b=b)

            return a.a() + b.b() + c.c()

        @self.container.autowire
        def autowired(a: A, b: B, c: C):
            return a.a() + b.b() + c.c()

        execution_time_baseline = timeit.timeit(native, number=iterations)
        execution_time_wireup = timeit.timeit(autowired, number=iterations)
        penalty = execution_time_wireup - execution_time_baseline

        print(f"{execution_time_baseline=}s")
        print(f"{execution_time_wireup=}s")
        print(f"{execution_time_wireup / execution_time_baseline = }x")
        print(f"{penalty=}s")
