# :thread: WireUp

Dependency and configuration injection library designed to provide a powerful and flexible way to
manage and inject dependencies across your application,
making it easier to develop, test, and maintain Python codebases.

## Key features

<div class="card-container">
    <div class="card">
        <div class="card-title">
            <img src="https://cdn.jsdelivr.net/gh/jdecked/twemoji@14.1.2/assets/72x72/27a1.png" /> 
            Dependency Injection
        </div>
        Effortlessly inject dependencies into your views, classes or functions using a clean and intuitive syntax.
    </div>
    <div class="card">
        <div class="card-title">
            <img src="https://cdn.jsdelivr.net/gh/jdecked/twemoji@14.1.2/assets/72x72/1f3ed.png" />
            Factory pattern
        </div>
        Optionally defer instantiation to specialized factories for full control over object creation.
    </div>
    <div class="card">
        <div class="card-title">
            <img src="https://cdn.jsdelivr.net/gh/jdecked/twemoji@14.1.2/assets/72x72/231b.png" /> 
            Lazy loading
        </div>
        Dependencies injected by the library are lazily loaded and will be only initialized on first use.
    </div>
    <div class="card">
        <div class="card-title">
            <img src="https://cdn.jsdelivr.net/gh/jdecked/twemoji@14.1.2/assets/72x72/31-20e3.png" /> 
            Singleton dependencies
        </div>
        Every dependency is initialized only once and all references to it will reuse the same instance.
    </div>
    <div class="card">
        <div class="card-title">
            <img src="https://cdn.jsdelivr.net/gh/jdecked/twemoji@14.1.2/assets/72x72/2699.png" /> 
            Configuration Management
        </div>
        Manage and inject application configuration values supporting parameter interpolation and referencing.
    </div>
    <div class="card">
        <div class="card-title">
            <img src="https://cdn.jsdelivr.net/gh/jdecked/twemoji@14.1.2/assets/72x72/23f0.png" /> 
            Async ready
        </div>
        Out of the box support for async code.
    </div>
    <div class="card">
        <div class="card-title">
            <img src="https://cdn.jsdelivr.net/gh/jdecked/twemoji@14.1.2/assets/72x72/2753.png" /> 
            Framework Agnostic
        </div>
        Seamlessly integrate with popular web frameworks like FastAPI and Flask to simplify dependency management in web applications.
    </div>
    <div class="card">
        <div class="card-title">
            <img src="https://cdn.jsdelivr.net/gh/jdecked/twemoji@14.1.2/assets/72x72/1f4cd.png" /> 
            Service/Configuration Locator
        </div>
        Dynamically retrieve services or configuration for more advanced use cases.
    </div>
</div>

## License

This project is licensed under the terms of the [MIT](https://github.com/maldoinc/wireup/blob/master/license.md){:
target=_blank } license.
