# WireUp

![GitHub](https://img.shields.io/github/license/maldoinc/wireup?style=for-the-badge)
![GitHub Workflow Status (with event)](https://img.shields.io/github/actions/workflow/status/maldoinc/wireup/run_all.yml?style=for-the-badge)
![Code Climate maintainability](https://img.shields.io/codeclimate/maintainability/maldoinc/wireup?style=for-the-badge&label=Code+Climate)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/wireup?style=for-the-badge)
![PyPI - Version](https://img.shields.io/pypi/v/wireup?style=for-the-badge)


Dependency injection library designed to provide a powerful and flexible way to manage and inject 
dependencies making it easier to develop, test, and maintain Python codebases.

---
## Quickstart guide

Demonstration of a simple application with two services (classes that provide functionality)
and parameters (app configuration) showing automatic dependency resolution and injection (autowiring) 
for services and a simple web view called "greet".

**1. Register dependencies**

```python
from wireup import container, Wire

# Parameters serve as configuration for services. 
# Populate this with your existing configuration
# Think of a database url or environment name.
container.params.update(...)


# Register a class as a dependency in the container.
# Constructor injection is supported for regular classes as well as dataclasses.
# In turn this can also depend on other objects in the container.
@container.register
class DbService:
    # Inject a parameter by name
    connection_str: Annotated[str, Wire(param="db.connection_str")],
    # Or by interpolating multiple parameters into a string
    cache_dir: Annotated[str, Wire(expr="${cache_dir}/${env}/db")],


@container.register
@dataclass
class UserRepository:
    db: DbService  # Services may also depend on other dependencies.
```

**2. Inject**

```python
@app.route("/greet/<str:name>")
@container.autowire
# Decorate all targets where the library must perform injection,such as views in a web app.
# Classes are automatically injected based on annotated type. 
# Parameters will be located based on their annotation metadata.
def greet(
    name: str, 
    user_repository: UserRepository,  
    env: Annotated[str, Wire(param="env")]
): 
    ...
```

**Installation**

```bash
# Install using poetry:
poetry add wireup

# Install using pip:
pip install wireup
```

## Documentation

For more information [check out the documentation](https://maldoinc.github.io/wireup)

## Demo application

A demo flask application is available at [maldoinc/wireup-demo](https://github.com/maldoinc/wireup-demo)
