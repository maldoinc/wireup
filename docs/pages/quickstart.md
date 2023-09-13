Demonstration of a simple application with two services (classes that provide functionality)
and parameters (app configuration) showing automatic dependency resolution and injection (autowiring) 
for services and a simple web view called "greet".

**1. Register dependencies**

```python
from wireup import container

# Parameters serve as configuration for services. 
# Think of a database url or environment name.
container.params.update({
    "db.connection_str": os.environ.get("DATABASE_URL") # (1)!
    "cache_dir": gettempdir(),
    "env": os.environ.get("ENV", "dev")
})


# Constructor injection is supported for regular classes as well as dataclasses
@container.register # (2)!
class DbService:
   # Inject a parameter by name
   connection_str: Annotated[str, Wire(param="db.connection_str")],
   # Or by interpolating multiple parameters into a string
   cache_dir: Annotated[str, Wire(expr="${cache_dir}/${env}/db")],

@container.register
@dataclass
class UserRepository:
    db: DbService  # Services may also depend on other dependencies. (3)!
```

1. Even though there are dots in parameter names, that not imply any nested structure. The parameter bag is a
   flat key-value store.
2. Decorators do not modify the classes in any way and only serve to collect metadata. This behavior can make
   testing a lot simpler as you can still instantiate this like a regular class in your tests.
3. Use type hints to tell the library what object to inject.

**2. Inject**

```python
@app.route("/greet/<str:name>")
@container.autowire  # (1)!
# Classes are automatically injected based on annotated type. 
# Parameters will be located based on their annotation metadata.
# Unknown arguments will not be processed.
def greet(
    name: str, 
    user_repository: UserRepository,  
    env: Annotated[str, Wire(param="env")]
): 
    ...
```

1. Decorate all methods where the library must perform injection. 
   We know that this will be used in conjunction with many other libraries, so WireUp will not throw on unknown
   parameters in order to let other decorators to do their job.

**Installation**

```bash
# Install using poetry:
poetry add wireup

# Install using pip:
pip install wireup
```
