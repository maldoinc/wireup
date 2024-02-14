Example showing a Database service, a repository and a web view which uses the repository to fetch all posts 
from a fictional blog db.

**1. Register dependencies**

```python
from wireup import container

container.params.update(app.config.items()) # (3)!


@container.register # (1)!
class DatabaseService:
    def __init__(self, connection_url: Annotated[str, Wire(param="db_connection_url")]):
        self.engine = create_engine(connection_url)


@container.register
@dataclass # (4)!
class PostRepository:
    db: DatabaseService # (2)!

    def find_all(self) -> list[Post]:
        return self.db.query...

```

1. Decorators do not modify the classes in any way and only serve to collect metadata. This behavior can make
   testing a lot simpler as you can still instantiate this like a regular class in your tests.
2.  * Use type hints to indicate which dependency to inject.
    * Services are automatically autowired and do not need the `@autowire` decorator
3. Optionally wire parameters, they serve as configuration for services. Think of a database url or environment name.
4. Initializer injection is supported for regular classes as well as dataclasses.

**2. Inject**

```python
@app.get("/posts")
@container.autowire # (1)!
def get_posts(post_repository: PostRepository):
    return post_repository.find_all()
```

1. Decorate all methods where the library must perform injection.
   Optional when using the [Flask integration](integrations/flask).


**Installation**

```bash
# Install using poetry:
poetry add wireup

# Install using pip:
pip install wireup
```
