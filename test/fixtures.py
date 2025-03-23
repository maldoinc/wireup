from dataclasses import dataclass


@dataclass
class Counter:
    count: int = 0

    def inc(self):
        self.count += 1


class FooBase:
    def __init__(self):
        self.foo = "foo"


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


class FooBarMultipleBases(FooBase, FooBaseAnother):
    def __init__(self):
        super().__init__()
        self.foo = "bar_multiple_bases"
