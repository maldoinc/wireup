from dataclasses import dataclass

from wireup._annotations import abstract, injectable


@dataclass
class Counter:
    count: int = 0

    def inc(self):
        self.count += 1


@abstract
class FooBase:
    def __init__(self):
        self.foo = "foo"


@abstract
class FooBaseAnother:
    def __init__(self):
        self.foo = "another_foo"


class FooBar(FooBase):
    def __init__(self):
        super().__init__()
        self.foo = "bar"


class FooBarChild(FooBar):
    def __init__(self):
        super().__init__()
        self.foo = "bar_child"


class FooBaz(FooBase):
    def __init__(self):
        super().__init__()
        self.foo = "baz"


@injectable
class FooBarMultipleBases(FooBase, FooBaseAnother):
    def __init__(self):
        super().__init__()
        self.foo = "bar_multiple_bases"
