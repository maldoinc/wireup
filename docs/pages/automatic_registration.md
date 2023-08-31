# Automatic Registration

The examples show the use of `@container.register` to mark each service. 
However, if all of them reside in a few select modules then it is possible to automatically register 
all of them, eliminating the need for the decorator.

To achieve that you can use `container.regiter_all_in_module(module, pattern = "*")` method.

Module represents the top level module containing all your services, optionally a `fnmatch` pattern can be specified
to only register classes that match the pattern. This does not support registering interfaces.

```python
container.register_all_in_module(app.service, "*Service")
```
****