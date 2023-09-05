# WireUp
Dependency and configuration injection library in Python.

**1. Set application configuration parameters** 
```python
container.params.update({
    "db.connection_str": "sqlite://memory",
    "auth.user": os.environ.get("USER"),
    "cache_dir": "/var/cache/",
    "env": os.environ.get("ENV", "dev")
})
```

**2. Register dependencies**

```python
@container.register
class DbService:
    def __init__(
        self,
        # Inject a parameter by name
        connection_str: str = wire(param="db.connection_str"),
        # Or by interpolating multiple parameters into a string
        cache_dir: str = wire(expr="${cache_dir}/${auth.user}/db"),
    ):
        self.connection_str = connection_str
        self.cache_dir = cache_dir
        
# Constructor injection is also supported for dataclasses
# resulting in a more compact syntax.
@container.register
@dataclass  
class UserRepository:
    db: DbService # Dependencies may also depend on other dependencies.
    user: str = container.wire(param="auth.user") 
```

**3. Inject**

```python
# Decorate all methods where the library must perform injection. 
@app.route("/greet/<str:name>")
@container.autowire
# Classes are automatically injected based on annotated type. 
# Parameters will be located based on the hint given in their default value.
# Unknown arguments will not be processed.
def greet(name: str, user_repository: UserRepository, env: str = wire(param="env")):
  ...
```

**Installation**
```bash
# Install using poetry:
poetry add wireup

# Install using pip:
pip install wireup
```

