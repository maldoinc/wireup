# :thread: WireUp
Dependency and configuration injection library in Python.

---

WireUp is a Python library designed to provide a powerful and flexible way to 
manage and inject dependencies across your application,
making it easier to develop, test, and maintain your codebase.

## Key features


**:arrow_right: Dependency Injection**
:   Effortlessly inject dependencies into your views, classes or functions using a clean and intuitive syntax.

**:factory: Factory pattern**
:   Optionally defer instantiation to specialized factories for full control over object creation.

**:hourglass: Lazy loading**
:   Dependencies injected by the library are lazily loaded and will be only initialized on first use.

**:one: Singleton dependencies**
:   Every dependency is initialized only once and all references to it will reuse the same instance.

**:gear: Configuration Management**
:   Manage and inject application configuration values supporting parameter interpolation and referencing.

**:alarm_clock: Async ready**
:   Out of the box support for async code.

**:question_mark: Framework Agnostic**
:   Seamlessly integrate with popular web frameworks like FastAPI and Flask to simplify dependency management in web applications.

**:round_pushpin: Service/Configuration Locator**
:   Dynamically retrieve services or configuration for more advanced use cases.

## License

This project is licensed under the terms of the [MIT](https://github.com/maldoinc/wireup/blob/master/license.md){: target=_blank } license.
