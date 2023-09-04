from test.services.db_service import DbService
from test.services.foo_service import FooService


class BazService:
    def __init__(self, foo: FooService, db: DbService) -> None:
        self.db = db
        self.foo = foo

    def baz(self) -> str:
        return f"baz {self.foo.bar()} - {self.db.get_result()}"
