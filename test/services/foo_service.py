from dataclasses import dataclass
from test.services.db_service import DbService


@dataclass
class FooService:
    db: DbService

    def bar(self):
        return self.db.get_result()
