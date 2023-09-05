# Automatic Registration

In addition to using `@container.register` to register each dependency, automatic registration is also possible by
using the `container.regiter_all_in_module(module, pattern = "*")` method.

Module represents the top level module containing all your dependencies, optionally a `fnmatch` pattern can be specified
to only register classes that match the pattern. This is the equivalent of using `@container.register`
on each.

```python
container.register_all_in_module(app.service, "*Service")
```
