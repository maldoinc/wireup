
import unittest
from wireup import instance, create_sync_container, Inject, injectable
from typing_extensions import Annotated


class TestInstanceIntegration(unittest.TestCase):
    def test_container_resolves_instance(self):
        class DbConnection:
            pass
            
        db = DbConnection()
        container = create_sync_container(injectables=[
            instance(db, as_type=DbConnection)
        ])
        
        self.assertIs(container.get(DbConnection), db)

    def test_container_resolves_qualified_instance(self):
        class DbConnection:
            pass
            
        primary = DbConnection()
        replica = DbConnection()
        
        container = create_sync_container(injectables=[
            instance(primary, as_type=DbConnection, qualifier="write"),
            instance(replica, as_type=DbConnection, qualifier="read"),
        ])
        
        self.assertIs(container.get(DbConnection, qualifier="write"), primary)
        self.assertIs(container.get(DbConnection, qualifier="read"), replica)

    def test_instance_injection_into_service(self):
        class DbConnection:
            pass
            
        @injectable
        class Repository:
            def __init__(self, db: DbConnection):
                self.db = db

        conn = DbConnection()
        container = create_sync_container(injectables=[
            instance(conn, as_type=DbConnection),
            Repository,
        ])
        
        repo = container.get(Repository)
        self.assertIs(repo.db, conn)

    def test_qualified_instance_injection_into_service(self):
        class DbConnection:
            pass
            
        @injectable
        class Service:
            def __init__(
                self, 
                primary: Annotated[DbConnection, Inject(qualifier="write")],
                replica: Annotated[DbConnection, Inject(qualifier="read")]
            ):
                self.primary = primary
                self.replica = replica

        primary = DbConnection()
        replica = DbConnection()

        
        container = create_sync_container(injectables=[
            instance(primary, as_type=DbConnection, qualifier="write"),
            instance(replica, as_type=DbConnection, qualifier="read"),
            Service,
        ])
        
        svc = container.get(Service)
        self.assertIs(svc.primary, primary)
        self.assertIs(svc.replica, replica)

    def test_duplicate_registration_fails(self):
        obj = object()
        with self.assertRaises(Exception): # wireup raises specific errors, but checking generic for robustness/completeness unless I import DuplicateServiceRegistrationError
            create_sync_container(injectables=[
                instance(obj, as_type=object),
                instance(obj, as_type=object),
            ])
