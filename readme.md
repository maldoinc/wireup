# WireUp

Effortless dependency injection in Python

**1. Register services with the container**

```python
@container.register
class DbService:
    def __init__(
        self,
        # Locate a parameter by name
        connection_str: str = wire(param="db.connection_str"),
        # Or by interpolating multiple parameters into a string
        cache_dir: str = wire(expr="${cache_dir}/${auth.user}/db"),
    ):
        self.connection_str = connection_str
        self.cache_dir = cache_dir
        
@container.register
@dataclass  # Constructor injection is also supported for dataclasses.
class UserRepository:
    db: DbService  # Services may also depend on any other services.
    user: str = conttainer.wire(param="auth.user") 
```

**2. Set your application's parameters in the container** 
```python
container.params.update({
    "db.connection_str": "sqlite://memory",
    "auth.user": os.environ.get("USER"),
    "cache_dir": "/var/cache/",
    "env": os.environ.get("ENV", "dev")
})
```

**3. Inject into classes, services or routes**

```python
# Decorate all the routes where the library must perform injection. 
@app.route("/<name>")
@container.autowire
# Classes are automatically injected based on annotated type. 
# Parameters will be located based on the hint given in their default value.
# Unknown arguments will not be processed.
def home(name: str, user_repository: UserRepository, env: str = wire(param="env")):
  ...
```

## Documentation

For more information [read our documentation](#)