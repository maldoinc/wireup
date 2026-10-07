from typing import Protocol

from wireup import injectable


class Greeter(Protocol):
    def hi(self) -> str: ...


@injectable(as_type=Greeter, qualifier="delta")
class Delta:
    def hi(self) -> str:
        return "delta"


@injectable(as_type=Greeter, qualifier="beta")
class Beta:
    def hi(self) -> str:
        return "beta"


@injectable(as_type=Greeter)
class Alpha:
    def hi(self) -> str:
        return "alpha"


@injectable(as_type=Greeter, qualifier="gamma")
class Gamma:
    def hi(self) -> str:
        return "gamma"
