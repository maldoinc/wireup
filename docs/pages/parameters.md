In addition to service objects, the container also holds configuration, called parameters.

Parameters are stored as a flat key-value store. They are able to retrieved at a later time by 
services when being constructed. They serve as configuration for services. 
Think of a database url or environment name.

## Management

Parameters are put in the container using its `params` property and are referenced by their name.
It is possible to add items by calling the `.put(name, value)` method, or in bulk or by calling `.update(dict)` 
using a dictionary of name-value pairs.

To retrieve a parameter by name directly from the container you can call `container.params.get(name)`.

!!! note
    Although the value of the parameters can be anything, they cannot depend on anything else.
    As such, autowiring services or other parameters on them is not possible.


## Injection

Contrary to services, it is not possible to autowire a parameter solely by its type. To enable autowiring you must
use the `wire()` method as the parameters default value.

### By name

To inject a parameter by name simply call `wire(param="param_name")`.

```python
@container.autowire
def do_something_cool(cache_dir: str = wire(param="cache_dir")) -> None:
    ...
```

### Parameter expressions

It is possible to interpolate parameters using a special syntax. This will enable you to retrieve several parameters
at once and concatenate their values together or simply format the value of a single parameter.

```python
@container.autowire
def do_something_cool(logs_cache_dir: str = wire(expr="${cache_dir}/${env}/logs")) -> None:
    ...
```

## Parameter enums

Parameter enums represent an alternative for those who do not want to rely on strings and want to have a typed
way to refer to parameter names. You can achieve this by creating a new type inheriting from `ParameterEnum`.

```python
class AppParameters(ParameterEnum):
    cache_dir = "cache_dir"
    # ... other params follow
```
Using this we can use the enum member whenever we want to refer to a particular parameter. The main feature of
the enum is a `wire()` method which is syntactic sugar for `wire(param=AppParameters.cache_dir.value)`

```python
container.params.put(AppParameters.cache_dir.value, "/var/cache")

@container.autowire
def do_something_cool(cache_dir: str = AppParameters.cache_dir.wire()) -> None:
    ...
```


