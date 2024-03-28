import unittest

from test.unit.services.no_annotations.db_service import DbService
from wireup.ioc.initialization_context import InitializationContext
from wireup.ioc.types import AnnotatedParameter


class InitializationContextTest(unittest.TestCase):
    def setUp(self):
        self.context = InitializationContext()

    def test_init_returns_false_when_known(self):
        self.assertTrue(self.context.init_target(self.setUp))
        self.assertFalse(self.context.init_target(self.setUp))

    def test_put_get(self):
        self.context.init_target(InitializationContextTest)
        self.context.add_dependency(InitializationContextTest, "foo", AnnotatedParameter(klass=DbService))

        self.assertEqual(
            self.context.dependencies[InitializationContextTest], {"foo": AnnotatedParameter(klass=DbService)}
        )
