import pytest
from typing import Annotated

from wireup import Inject, create_sync_container, injectable, instance


def test_instance_registration():
    class DbConnection:
        pass

    @injectable
    class Repository:
        def __init__(self, db_conn: DbConnection):
            self.db_conn = db_conn

    db = DbConnection()
    container = create_sync_container(injectables=[instance(db, as_type=DbConnection), Repository])

    # Check it is registered as a singleton with the desired type
    assert container.get(DbConnection) is db
    assert container.get(DbConnection) is container.get(DbConnection)

    repo = container.get(Repository)
    assert repo.db_conn is db


def test_instance_registration_with_qualifier():
    class DbConnection:
        pass

    @injectable
    class Service:
        def __init__(
            self,
            write_db: Annotated[DbConnection, Inject(qualifier="write")],
            read_db: Annotated[DbConnection, Inject(qualifier="read")],
        ):
            self.write_db = write_db
            self.read_db = read_db

    primary = DbConnection()
    replica = DbConnection()

    container = create_sync_container(
        injectables=[
            instance(primary, as_type=DbConnection, qualifier="write"),
            instance(replica, as_type=DbConnection, qualifier="read"),
            Service,
        ]
    )

    assert container.get(DbConnection, qualifier="write") is primary
    assert container.get(DbConnection, qualifier="read") is replica

    svc = container.get(Service)

    assert svc.write_db is primary
    assert svc.read_db is replica


def test_duplicate_registration_fails():
    obj = object()

    # wireup throws specific Exception subclasses but Exception is fine for basic tests
    with pytest.raises(Exception):
        create_sync_container(
            injectables=[
                instance(obj, as_type=object),
                instance(obj, as_type=object),
            ]
        )
