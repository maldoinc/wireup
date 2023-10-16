The container can be adjusted for either short or long-lived processes. A short-lived process may be a cli
command that is part of a broader application. Whereas a long-lived process may be an Api that listens
and serves requests.

!!! note
    To warm up, use `warmup_container` from the `wireup` module.

## Under the hood

When decorating with `@register` or `@autowire`, the container doesn't know yet the final set of services
so when it performs autowiring it injects proxy objects. These act and behave the same way as the real ones but there
is a tiny performance penalty when interacting with them.

During warmup, the container will assume the current dependency set is the final one and will create only real instances
for singleton dependencies that way during autowiring there will be no more proxies.

## Recommendations

* For simple commands which will perform a small number of tasks then exit it is recommended to not use 
`warmup_container`. This will mean that only objects used during the lifetime of the command will be used
instead of instantiating all services.
* For long-lived processes where all these objects will be instantiated anyway, it is recommended to use
 `warmup_container` to minimize performance penalty incurred by autowiring.
