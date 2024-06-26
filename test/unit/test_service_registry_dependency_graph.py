import unittest

from wireup import ServiceLifetime
from wireup.ioc.service_registry import ServiceRegistry


class TestServiceRegistry(unittest.TestCase):
    def setUp(self):
        self.registry = ServiceRegistry()

    def test_dependency_graph_empty(self):
        graph = self.registry.get_dependency_graph()
        self.assertEqual(graph, {})

    def test_dependency_graph_singleton(self):
        class SingletonService:
            pass

        self.registry.register_service(SingletonService, qualifier=None, lifetime=ServiceLifetime.SINGLETON)

        graph = self.registry.get_dependency_graph()
        self.assertEqual(graph, {SingletonService: set()})

    def test_dependency_graph_transient(self):
        # Register a transient service and check the dependency graph.
        class TransientService:
            pass

        self.registry.register_service(TransientService, qualifier=None, lifetime=ServiceLifetime.TRANSIENT)

        graph = self.registry.get_dependency_graph()
        self.assertEqual(graph, {})

    def test_dependency_graph_with_dependencies(self):
        class DependencyA:
            pass

        class DependencyB:
            pass

        class ServiceWithDependencies:
            def __init__(self, a: DependencyA, b: DependencyB):
                self.a = a
                self.b = b

        self.registry.register_service(DependencyA, qualifier=None, lifetime=ServiceLifetime.SINGLETON)
        self.registry.register_service(DependencyB, qualifier=None, lifetime=ServiceLifetime.SINGLETON)
        self.registry.register_service(ServiceWithDependencies, qualifier=None, lifetime=ServiceLifetime.SINGLETON)

        graph = self.registry.get_dependency_graph()
        self.assertEqual(
            graph, {DependencyA: set(), DependencyB: set(), ServiceWithDependencies: {DependencyA, DependencyB}}
        )

    def test_dependency_graph_with_interface(self):
        class MyInterface:
            pass

        class ImplementationA(MyInterface):
            pass

        class ImplementationB(MyInterface):
            pass

        class ServiceWithInterface:
            def __init__(self, iface: MyInterface):
                self.iface = iface

        self.registry.register_abstract(MyInterface)
        self.registry.register_service(ImplementationA, qualifier="A", lifetime=ServiceLifetime.SINGLETON)
        self.registry.register_service(ImplementationB, qualifier="B", lifetime=ServiceLifetime.SINGLETON)
        self.registry.register_service(ServiceWithInterface, qualifier=None, lifetime=ServiceLifetime.SINGLETON)

        graph = self.registry.get_dependency_graph()
        self.assertEqual(
            graph,
            {ImplementationA: set(), ImplementationB: set(), ServiceWithInterface: {ImplementationA, ImplementationB}},
        )

    def test_dependency_graph_with_transient_interfaces(self):
        class MyInterface:
            pass

        class ImplementationA(MyInterface):
            pass

        class ImplementationB(MyInterface):
            pass

        class ServiceWithInterface:
            def __init__(self, iface: MyInterface):
                self.iface = iface

        self.registry.register_abstract(MyInterface)
        self.registry.register_service(ImplementationA, qualifier="A", lifetime=ServiceLifetime.TRANSIENT)
        self.registry.register_service(ImplementationB, qualifier="B", lifetime=ServiceLifetime.TRANSIENT)
        self.registry.register_service(ServiceWithInterface, qualifier=None, lifetime=ServiceLifetime.SINGLETON)

        graph = self.registry.get_dependency_graph()
        self.assertEqual(graph, {ServiceWithInterface: set()})

    def test_dependency_graph_with_factory(self):
        class MyService:
            pass

        def create_my_service() -> MyService:
            return MyService()

        self.registry.register_factory(create_my_service, lifetime=ServiceLifetime.SINGLETON)

        graph = self.registry.get_dependency_graph()
        self.assertEqual(graph, {MyService: set()})
