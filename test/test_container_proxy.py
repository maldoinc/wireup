import unittest
from test.services.no_annotations.random.random_service import RandomService
from test.services.no_annotations.random.truly_random_service import TrulyRandomService

from wireup.ioc.proxy import ContainerProxy


class ContainerProxyTest(unittest.TestCase):
    def test_getattr_proxies_call(self):
        is_created = False

        def get_random_service():
            nonlocal is_created
            is_created = True
            return RandomService()

        proxy = ContainerProxy(get_random_service)
        self.assertFalse(is_created)
        self.assertEqual(4, proxy.get_random())
        self.assertTrue(is_created)

    def test_setattr_proxies_call(self):
        is_created = False

        def get_random_service():
            nonlocal is_created
            is_created = True
            return TrulyRandomService(RandomService())

        proxy = ContainerProxy(get_random_service)
        self.assertFalse(is_created)
        proxy.random_service = None
        self.assertTrue(is_created)
        self.assertIsNone(proxy.random_service)
