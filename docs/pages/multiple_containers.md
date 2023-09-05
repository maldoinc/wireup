# Multiple Containers

As each container has its own state and does not modify the underlying classes, use of multiple containers is possible.
A few things to keep in mind when using multiple containers.

* The default `wireup.container` is simply an instance just like any other.
* If a service belongs to multiple containers you can use decorators on them, but it is preferable you manage
register services without the decorators.
* To wire parameters use initialization context or the `wire` method. The `wire` method is not bound to any single
container but merely provides hints as to what should be injected. These hints can be read by any container
when calling autowire.
* Use of `@autowire` decorator with multiple containers is unsupported. To bind parameters and services to a method
call `instance.autowire(fn)()`. The autowire method will return a function where all the arguments that the container
knows about are passed.