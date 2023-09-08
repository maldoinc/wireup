from unittest import TestCase

from wireup import ParameterEnum, ParameterBag, ParameterWrapper, DependencyContainer


class ParameterEnumTest(TestCase):
    def def_enum_wire_returns_param_wrapper(self):
        class DbParams(ParameterEnum):
            connection_str = "db.connection_str"

        bag = ParameterBag()
        bag.put(DbParams.connection_str.value, "sqlite://")

        param_ref = DbParams.connection_str.wire()
        self.assertEqual(param_ref, ParameterWrapper("db.connection_str"))

    def test_can_inject_parameter_enums(self):
        class DbParams(ParameterEnum):
            connection_str = "db.connection_str"

        container = DependencyContainer(ParameterBag())
        container.params.put(DbParams.connection_str.value, "sqlite://")

        @container.autowire
        def inner(connection_str=DbParams.connection_str.wire()):
            self.assertEqual(connection_str, "sqlite://")

        inner()
