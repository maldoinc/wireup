# Automatic Registration

The examples show the use of `@container.wire` to mark each service. 
However, if all of them reside in a few select modules then it is possible to automatically register 
all of them, eliminating the need for the decorator.

To achieve that you can use `container.regiter_all_in_module(module, pattern = "*")` method.

Module represents the top level module containing all your services, optionally a `fnmatch` pattern can be specified
to only register classes that match the pattern.

```python
container.register_all_in_module(app.service, "*Service")
```
****