from dataclasses import dataclass


@dataclass
class Counter:
    count: int = 0

    def inc(self):
        self.count += 1


class FooBase:
    def __init__(self):
        self.foo = "foo"


class FooBar(FooBase):
    def __init__(self):
        super().__init__()
        self.foo = "bar"


class FooBaz(FooBase):
    def __init__(self):
        super().__init__()
        self.foo = "baz"
