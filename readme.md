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

Example showing a Database service, a repository and a web view which uses the repository to fetch all posts 
from a fictional blog db.

**1. Register dependencies**

```python
from wireup import container

# Parameters serve as configuration for services. 
# Think of a database url or environment name.
container.params.update(existing_dict_config)


# Register a class as a service in the container.
@container.register 
class DatabaseService:
    # connection_url will contain the value of the parameter 
    # with the given name in the annotation.
    def __init__(self, connection_url: Annotated[str, Wire(param="db_connection_url")]):
        self.engine = create_engine(connection_url)

        
# Initializer injection is supported for regular classes as well as dataclasses.
@container.register
@dataclass
class PostRepository:
    db: DatabaseService 

    def find_all(self) -> list[Post]:
        return self.db.query...
```

**2. Inject**

```python
@app.get("/posts")
@container.autowire 
# Decorate all targets where the library must perform injection,such as views in a web app.
# Services are automatically injected based on annotated type. 
def get_posts(post_repository: PostRepository):
    return post_repository.find_all()
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
