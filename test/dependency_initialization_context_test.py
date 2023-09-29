import unittest

# from wireup.ioc.container_util import DependencyInitializationContext, ParameterWrapper


# class TestDependencyInitializationContext(unittest.TestCase):
#     def test_add_param(self):
#         context = DependencyInitializationContext()
#         param_ref = "param_key"
#         context.add_param(Foo, "arg_name", param_ref)
#
#         expected_context = {Foo: {"arg_name": ParameterWrapper(param_ref)}}
#
#         self.assertEqual(context.context, expected_context)
#
#     def test_update(self):
#         context = DependencyInitializationContext()
#         context.update(Foo, {"arg1": "param1", "arg2": "param2"})
#
#         expected_context = {Foo: {"arg1": ParameterWrapper("param1"), "arg2": ParameterWrapper("param2")}}
#         self.assertEqual(context.context, expected_context)
#
#         context.update(Foo, {"arg2": "new_param2", "arg3": "param3"})
#         expected_context = {
#             Foo: {
#                 "arg1": ParameterWrapper("param1"),
#                 "arg2": ParameterWrapper("new_param2"),
#                 "arg3": ParameterWrapper("param3"),
#             }
#         }
#
#         self.assertEqual(context.context, expected_context)
#
#
# class Foo:
#     ...
