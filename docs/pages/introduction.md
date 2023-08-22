# Introduction

WireUp is a Python library designed to simplify the management of dependencies in your projects. 
It provides a powerful and flexible way to manage and inject dependencies across your application, 
making it easier to develop, test, and maintain your codebase.

Key features include:

- **Dependency Injection:** Effortlessly inject dependencies into your classes and functions using a clean and intuitive syntax.
- **Lazy loading:** Dependencies injected by the library are lazily loaded and will be only initialized on first use. This applies both to autowired arguments and other dependencies injected in services.
- **Singleton dependencies:** Every dependency is initialized only once and all references to it will reuse the same instance.
- **Parameter Management:** Manage your application's parameters and configuration values supporting parameter interpolation and referencing.
- **Framework Integration:** Seamlessly integrate with popular web frameworks like FastAPI and Flask to simplify dependency management in web applications.
- **Service Locator:** You can use the container to retrieve classes by their type for more advanced use cases.
