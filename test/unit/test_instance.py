from typing_extensions import Annotated

import pytest
from wireup import Inject, create_sync_container, injectable, instance
from wireup.errors import DuplicateServiceRegistrationError


def test_instance_registration():
    class DbConnection:
        pass

    @injectable
    class Repository:
        def __init__(self, db_conn: DbConnection):
            self.db_conn = db_conn

    db = DbConnection()
    container = create_sync_container(
        injectables=[instance(db, as_type=DbConnection), Repository]
    )
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
    with pytest.raises(DuplicateServiceRegistrationError):
        create_sync_container(
            injectables=[
                instance(obj, as_type=object),
                instance(obj, as_type=object),
            ]
        )


def test_instance_registration_type_mismatch_fails():
    from wireup.errors import AsTypeMismatchError

    class A:
        pass

    class B:
        pass

    with pytest.raises(AsTypeMismatchError):
        create_sync_container(injectables=[instance(A(), as_type=B)])
