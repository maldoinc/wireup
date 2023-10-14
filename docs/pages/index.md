# :thread: WireUp

Dependency injection library designed to provide a powerful and flexible way to
manage and inject dependencies making it easier to develop, test, and maintain Python codebases.

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
            <img src="https://cdn.jsdelivr.net/gh/jdecked/twemoji@14.1.2/assets/72x72/2699.png" /> 
            Configuration is also a dependency!
        </div>
        Inject configuration instead of retrieving it manually.
        Avoid having a hard dependency on the object that stores the configuration.
    </div>
    <div class="card">
        <div class="card-title">
            <img src="https://cdn.jsdelivr.net/gh/jdecked/twemoji@14.1.2/assets/72x72/231b.png" /> 
            Short and long-lived processes
        </div>
        Suitable for use in long-running as well as short-lived processes.
        Preload services for performance or lazily inject to instantiate only what you use.
    </div>

    <div class="card">
        <div class="card-title">
            <img src="https://cdn.jsdelivr.net/gh/jdecked/twemoji@14.1.2/assets/72x72/1f4dc.png" /> 
            Interfaces / Abstract classes
        </div>
        Define abstract types and have the container automatically inject the implementation.
        Say goodbye to mocks in your tests!
    </div>
    <div class="card">
        <div class="card-title">
            <img src="https://cdn.jsdelivr.net/gh/jdecked/twemoji@14.1.2/assets/72x72/1f465.png" /> 
            Multiple Containers
        </div>
        Use the provided container or instantiate and use multiple ones depending on your project's needs.
    </div>
    <div class="card">
        <div class="card-title">
            <img src="https://cdn.jsdelivr.net/gh/jdecked/twemoji@14.1.2/assets/72x72/1f3ed.png" />
            Factory pattern
        </div>
        Defer instantiation to specialized factories for full control over object creation when necessary.
    </div>
    <div class="card">
        <div class="card-title">
            <img src="https://cdn.jsdelivr.net/gh/jdecked/twemoji@14.1.2/assets/72x72/31-20e3.png" /> 
            Singletons/Transient dependencies
        </div>
        Declare dependencies as transient or singletons which tells the container whether 
        to inject a fresh copy or reuse existing instances.
    </div>
    <div class="card">
        <div class="card-title">
            <img src="https://cdn.jsdelivr.net/gh/jdecked/twemoji@14.1.2/assets/72x72/2753.png" /> 
            Framework Agnostic
        </div>
        Seamlessly integrate with popular web frameworks like Django, Flask and FastAPI
        to simplify dependency management.
    </div>

</div>

## License

This project is licensed under the terms of the
[MIT](https://github.com/maldoinc/wireup/blob/master/license.md){: target=_blank } license.
