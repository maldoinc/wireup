import unittest
from collections.abc import Sequence

import wireup

from test.unit.services.collection_scan import greeters


class DiscoveryOrderTest(unittest.TestCase):
    def test_module_scan_collection_injection_has_deterministic_order(self):
        container = wireup.create_sync_container(injectables=[greeters])
        result = [g.hi() for g in container.get(Sequence[greeters.Greeter])]

        self.assertEqual(["delta", "beta", "alpha", "gamma"], result)

    def test_module_scan_discovery_order_is_stable_across_repeated_scans(self):
        first = [g.hi() for g in wireup.create_sync_container(injectables=[greeters]).get(Sequence[greeters.Greeter])]
        second = [g.hi() for g in wireup.create_sync_container(injectables=[greeters]).get(Sequence[greeters.Greeter])]

        self.assertEqual(first, second)
