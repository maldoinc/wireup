<div align="center">
<h1>Wireup</h1>
<p>Dependency Injection Container with a focus on developer experience, type safety and ease of use.</p>

[![GitHub](https://img.shields.io/github/license/maldoinc/wireup)](https://github.com/maldoinc/wireup)
[![GitHub Workflow Status (with event)](https://img.shields.io/github/actions/workflow/status/maldoinc/wireup/run_all.yml)](https://github.com/maldoinc/wireup)
[![Code Climate maintainability](https://img.shields.io/codeclimate/maintainability/maldoinc/wireup?label=Code+Climate)](https://codeclimate.com/github/maldoinc/wireup)
[![Coverage](https://img.shields.io/codeclimate/coverage/maldoinc/wireup?label=Coverage)](https://codeclimate.com/github/maldoinc/wireup)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/wireup)](https://pypi.org/project/wireup/)
[![PyPI - Version](https://img.shields.io/pypi/v/wireup)](https://pypi.org/project/wireup/)
</div>

> [!TIP]
>    Simplify Dependency injection for Flask using the new
[Flask integration](https://maldoinc.github.io/wireup/latest/flask_integration/)!
>
>    * Automatically inject dependencies without having to manually call autowire.
>    * Expose flask application configuration in the container.

---

## ⚡ Key Features
* Inject Services and Configuration
* Interfaces / Abstract classes
* Multiple Containers 
* Static factories
* Singleton/Transient dependencies
* Framework Agnostic
* Simplified usage in Flask and FastAPI using the first-party integrations.

## 📋 Quickstart

Example showing a Database service, a repository and a web view which uses the repository to fetch all posts 
from a fictional blog db.

**1. Register dependencies**

```python
from wireup import container

# Optionally wire parameters, they serve as configuration for services. 
# Think of a database url or environment name.
container.params.update(app.config.items())


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
# Decorate all targets where the library must perform injection, such as views in an Api.
# Services are automatically injected based on annotated type.
# Optional for views when using flask or fastapi integration.
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

## 📑 Documentation

For more information [check out the documentation](https://maldoinc.github.io/wireup)

## 🎮 Demo application

A demo flask application is available at [maldoinc/wireup-demo](https://github.com/maldoinc/wireup-demo)
