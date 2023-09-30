import timeit
import unittest
from dataclasses import dataclass
from typing import Optional

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
        def autowired(
            a: A,
            b: B,
            c: C,
            param: Annotated[str, Wire(param="start")],
            e: int = 0,
            f: float = 0,
            g: float = 0,
            h: Optional[unittest.TestCase] = None,
            i: unittest.TestCase = None,
        ):
            return a.a() + b.b() + c.c()

        execution_time_native_py = timeit.timeit(native, number=iterations)
        execution_time_injected = timeit.timeit(autowired, number=iterations)
        penalty = execution_time_injected - execution_time_native_py

        print(f"{execution_time_native_py=}s")
        print(f"{execution_time_injected=}s")
        print(f"{execution_time_injected / execution_time_native_py = }x")
        print(f"{penalty=}s")
