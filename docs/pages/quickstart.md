**1. Set application configuration parameters**

```python 
from wireup import container

container.params.update({
    "db.connection_str": os.environ.get("DATABASE_URL")# (1)!
    "service_auth.user": os.environ.get("SVC_USER"),
    "cache_dir": gettempdir(),
    "env": os.environ.get("ENV", "dev")
})
```

1. Even though there are dots that does in parameter names, that not imply any nested structure. The parameter bag is a
   flat key-value store.

**2. Register dependencies**

```python
@container.register# (1)!
class DbService:
    def __init__(
            self,
            # Inject a parameter by name
            connection_str: str = wire(param="db.connection_str"),
            # Or by interpolating multiple parameters into a string
            cache_dir: str = wire(expr="${cache_dir}/${service_auth.user}/db"),
    ):
        self.connection_str = connection_str
        self.cache_dir = cache_dir


# Constructor injection is also supported for dataclasses
# resulting in a more compact syntax.
@container.register
@dataclass
class UserRepository:
    db: DbService  # Dependencies may also depend on other dependencies. (2)!
```

1. The decorators do not modify the classes in any way and only serve to collect metadata. This behavior can make
   testing a lot simpler as you can still instantiate this like a regular class in your tests.
2. Use type hints to tell the library what object to inject.

**3. Inject**

```python
# Decorate all methods where the library must perform injection. 
@app.route("/greet/<str:name>")
@container.autowire
# Classes are automatically injected based on annotated type. 
# Parameters will be located based on the hint given in their default value.
# Unknown arguments will not be processed.
def greet(name: str, user_repository: UserRepository, env: str = wire(param="env")):# (1)!
    ...
```

1. We know that this will be used in conjunction with many other libraries, so WireUp will not throw on unknown
   parameters in order to let other decorators to do their job.

**Installation**

```bash
# Install using poetry:
poetry add wireup

# Install using pip:
pip install wireup
```
