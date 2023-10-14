The container can be adjusted for either short or long-lived processes. A short-lived process may be a cli
command that is part of a broader application. Whereas a long-lived process may be an Api that listens
and serves requests.

To performa a warmup of the container, use `initialize_container` from the `wireup` module.

```python
wireup.initialize_container(container, [services])
```

Pass the container and a list of top-level modules housing all service objects with container registrations.
This will load them, triggering the registration process for all services after which the container will
create and initialize all singleton objects and keep them in memory.

This will result in a speedup when interacting with service objects as they will be real instances of services
instead of proxy objects.


When `initialize_container` is not called the container will generate proxy objects and only when you first interact
with them will it create instances of services. This is what enables lazy-loading but there is a tiny performance
cost because the proxy object has to proxy all attr access to the real instance.

## Recommendations

* For simple commands which will perform a small number of tasks then exit it is recommended to not use 
`initialize_container`. This will mean that only objects used during the lifetime of the command will be used
instead of instantiating all services.
* For long-lived processes where all these objects will be instantiated anyway, it is recommended to use
 `initialize_container` to minimize performance penalty incurred by autowiring.
