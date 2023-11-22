from dataclasses import dataclass
from test.services.no_annotations.db_service import DbService


@dataclass
class FooService:
    db: DbService

    def bar(self):
        return self.db.get_result()
