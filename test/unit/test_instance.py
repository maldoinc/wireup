
import unittest
from wireup import instance
from wireup._annotations import InjectableDeclaration

class TestInstanceProvider(unittest.TestCase):
    def test_instance_helper_creates_valid_declaration(self):
        obj = object()
        provider = instance(obj, as_type=object)
        
        self.assertTrue(callable(provider))
        self.assertIs(provider(), obj)
        self.assertEqual(provider.__annotations__["return"], object)
        
        reg = provider.__wireup_registration__
        self.assertIsInstance(reg, InjectableDeclaration)
        self.assertIs(reg.obj, provider)
        self.assertEqual(reg.lifetime, "singleton")
        self.assertEqual(reg.as_type, object)
        self.assertIsNone(reg.qualifier)

    def test_instance_helper_supports_qualifiers(self):
        obj = {}
        provider = instance(obj, as_type=dict, qualifier="config")
        
        reg = provider.__wireup_registration__
        self.assertEqual(reg.qualifier, "config")
        self.assertIs(reg.as_type, dict)

    def test_instance_raises_if_as_type_is_missing(self):
        with self.assertRaisesRegex(ValueError, "Argument 'as_type' is required"):
            instance(object())

    def test_provider_always_returns_same_instance(self):
        obj = []
        provider = instance(obj, as_type=list)
        
        self.assertIs(provider(), obj)
        self.assertIs(provider(), obj)
