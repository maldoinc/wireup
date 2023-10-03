from __future__ import annotations

from typing import Any, Callable, Generic, TypeVar

__T = TypeVar("__T")


class ContainerProxy(Generic[__T]):
    """A proxy object used by the container to achieve lazy loading.

    Contains a reference to the final initialized object and proxies all requests to the instance.
    """

    __slots__ = ("__supplier", "__proxy_object")

    def __init__(self, instance_supplier: Callable[[], __T]) -> None:
        """Initialize a ContainerProxy.

        :param instance_supplier: A callable which takes no arguments and returns the object. Will be called to
        retrieve the actual instance when the objects' properties are first being accessed.
        """
        self.__supplier = instance_supplier
        self.__proxy_object: __T | None = None

    def __getattr__(self, name: Any) -> Any:
        """Intercept object property access and forwards them to the proxied object.

        If the proxied object has not been initialized yet, a call to instance_supplier is made to retrieve it.

        :param name: Attribute name being accessed
        """
        if not self.__proxy_object:
            self.__proxy_object = self.__supplier()

        return getattr(self.__proxy_object, name)
