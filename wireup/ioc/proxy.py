from __future__ import annotations

from typing import Any, Callable, Generic, TypeVar

T = TypeVar("T")


class ContainerProxy(Generic[T]):
    """A proxy object used by the container to achieve lazy loading.

    Contains a reference to the final initialized object and proxies all requests to the instance.
    """

    __slots__ = ("__supplier", "__proxy_object")

    def __init__(self, instance_supplier: Callable[[], T]) -> None:
        """Initialize a ContainerProxy.

        :param instance_supplier: A callable which takes no arguments and returns the object. Will be called to
        retrieve the actual instance when the objects' properties are first being accessed.
        """
        super().__setattr__("_ContainerProxy__supplier", instance_supplier)
        super().__setattr__("_ContainerProxy__proxy_object", None)

    def __getattr__(self, name: Any) -> Any:
        """Intercept object property access and forwards them to the proxied object.

        If the proxied object has not been initialized yet, a call to instance_supplier is made to retrieve it.

        :param name: Attribute name being accessed
        """
        proxy = getattr(self, "_ContainerProxy__proxy_object")  # noqa: B009

        if proxy is None:
            proxy = getattr(self, "_ContainerProxy__supplier")()  # noqa: B009
            super().__setattr__("_ContainerProxy__proxy_object", proxy)
        return getattr(proxy, name)

    def __setattr__(self, name: str, value: Any | None) -> None:
        """Intercept and pass attr writes to the proxied object."""
        proxy = getattr(self, "_ContainerProxy__proxy_object")  # noqa: B009

        if proxy is None:
            proxy = getattr(self, "_ContainerProxy__supplier")()  # noqa: B009
            super().__setattr__("_ContainerProxy__proxy_object", proxy)

        setattr(self.__proxy_object, name, value)
