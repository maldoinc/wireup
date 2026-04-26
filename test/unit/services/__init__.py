from wireup import injectable

from test.unit.services.abstract_multiple_bases import FooBase, FooBaseAnother


@injectable
class Greeter:
    def greet(self, name: str) -> str:
        return f"Hello {name}"


__all__ = ["FooBase", "FooBaseAnother", "Greeter"]
