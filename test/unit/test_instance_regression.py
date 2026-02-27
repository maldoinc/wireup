
import unittest
from wireup import instance, create_sync_container, injectable

class TestInstanceRegression(unittest.TestCase):
    def test_legacy_factory_workflow_parity(self):
        # 1. Old Service (Legacy Workaround)
        class OldService:
            pass
            
        old_instance = OldService()
        
        @injectable(as_type=OldService)
        def old_factory() -> OldService:
            return old_instance


        # 2. New Service (New Helper)
        class NewService:
            pass
            
        new_instance = NewService()

        # 3. Container with both
        container = create_sync_container(injectables=[
            old_factory,
            instance(new_instance, as_type=NewService)
        ])

        # Assert behavior is identical
        retrieved_old = container.get(OldService)
        retrieved_new = container.get(NewService)
        
        self.assertIs(retrieved_old, old_instance)
        self.assertIs(retrieved_new, new_instance)
        
        # Verify both are singletons (repeated calls return same object)
        self.assertIs(container.get(OldService), old_instance)
        self.assertIs(container.get(NewService), new_instance)

    def test_parity_with_manual_registration(self):
        # Verify that instance() produces similar internal metadata to a manual registration
        # This acts as a regression test to ensure our helper isn't doing something "weird"
        # compared to standard usage.
        
        obj = object()
        
        @injectable(as_type=object)
        def factory() -> object:
            return obj

            
        helper = instance(obj, as_type=object)
        
        # Check __wireup_registration__
        reg_factory = factory.__wireup_registration__
        reg_helper = helper.__wireup_registration__
        
        self.assertEqual(reg_factory.lifetime, reg_helper.lifetime)
        self.assertEqual(reg_factory.as_type, reg_helper.as_type)
        self.assertEqual(reg_factory.qualifier, reg_helper.qualifier)
