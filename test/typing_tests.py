from collections.abc import Callable, Hashable
from typing import Annotated, Any, TypeVar

from typing_extensions import ParamSpec, TypeAliasType, TypeForm, assert_type
from wireup import (
    AsyncContainer,
    Inject,
    Injected,
    ScopedAsyncContainer,
    ScopedSyncContainer,
    SyncContainer,
    create_async_container,
    create_sync_container,
    inject_from_container,
    injectable,
    instance,
    qualified,
    wrap_with_dependencies,
)


@injectable
class Repository:
    def __init__(self, name: Annotated[str, Inject(config="repository_name")] = "default") -> None:
        assert_type(name, str)
        self.name = name


@injectable(lifetime="scoped")
class Service:
    def __init__(self, repository: Repository) -> None:
        assert_type(repository, Repository)
        self.repository = repository


@injectable
def make_repository(name: Annotated[str, Inject(config="repository_name")] = "factory") -> Repository:
    assert_type(name, str)
    return Repository(name)


@injectable(lifetime="scoped")
async def make_service(repository: Repository) -> Service:
    return Service(repository)


def check_declarations() -> None:
    assert_type(Repository(), Repository)
    assert_type(Repository(name="example").name, str)
    assert_type(Service(Repository()), Service)
    assert_type(make_repository(name="example"), Repository)
    assert_type(injectable(make_repository)(), Repository)
    assert_type(injectable(qualifier="named")(make_repository)(), Repository)
    assert_type(instance(Repository(), as_type=Repository)(), Repository)

    Repository(123)  # type: ignore[arg-type]
    Service("invalid")  # type: ignore[arg-type]
    make_repository(name=123)  # type: ignore[arg-type]


def check_sync_container() -> None:
    container = create_sync_container(injectables=[Repository, Service])
    assert_type(container, SyncContainer)
    assert_type(container.get(Repository), Repository)
    assert_type(container.get(Repository, qualifier="named"), Repository)
    assert_type(container.get(list[Repository]), list[Repository])
    with container.enter_scope() as scope:
        assert_type(scope, ScopedSyncContainer)
        assert_type(scope.get(Service), Service)
        assert_type(scope.get(list[Service]), list[Service])

    @inject_from_container(container)
    def handler(value: int, repository: Injected[Repository]) -> str:
        assert_type(repository, Repository)
        return f"{repository.name}: {value}"

    assert_type(handler(1), str)


async def check_async_container() -> None:
    assert_type(await make_service(Repository()), Service)
    container = create_async_container(injectables=[Repository, make_service])
    assert_type(container, AsyncContainer)
    assert_type(await container.get(Repository), Repository)
    assert_type(await container.get(Repository, qualifier="named"), Repository)
    async with container.enter_scope() as scope:
        assert_type(scope, ScopedAsyncContainer)
        assert_type(await scope.get(Service), Service)
        assert_type(await scope.get(list[Service]), list[Service])

    @inject_from_container(container)
    async def handler(value: int, service: Injected[Service]) -> str:
        assert_type(service, Service)
        return f"{service.repository.name}: {value}"

    assert_type(await handler(1), str)
    await make_service("invalid")  # type: ignore[arg-type]


def check_injected_annotations(
    repository: Injected[Repository],
    optional: Injected[Repository | None],
    repositories: Injected[list[Repository]],
    named: Annotated[Repository, Inject(qualifier="named")],
    config: Annotated[str, Inject(config="name")],
) -> None:
    assert_type(repository, Repository)
    assert_type(optional, Repository | None)
    assert_type(repositories, list[Repository])
    assert_type(named, Repository)
    assert_type(config, str)


P = ParamSpec("P")
R = TypeVar("R")


def with_repository(target: Callable[P, R]) -> Callable[P, R]:
    @wrap_with_dependencies(target)
    def wrapper(*args: Any, repository: Injected[Repository], **kwargs: Any) -> R:
        assert_type(repository, Repository)
        return target(*args, **kwargs)

    return wrapper


@with_repository
def wrapped(value: int, /, *, suffix: str = "!") -> str:
    return f"{value}{suffix}"


@with_repository
async def async_wrapped(value: int, /, *, suffix: str = "!") -> str:
    return f"{value}{suffix}"


async def check_wrappers() -> None:
    assert_type(wrapped(1, suffix="."), str)
    assert_type(await async_wrapped(1, suffix="."), str)
    wrapped("invalid")  # type: ignore[arg-type]
    wrapped(1, suffix=123)  # type: ignore[arg-type]
    wrapped(value=1)  # type: ignore[call-arg]
    wrapped()  # type: ignore[call-arg]
    await async_wrapped("invalid")  # type: ignore[arg-type]


RepositorySelector = TypeAliasType("RepositorySelector", Callable[[str], Repository])


def check_type_expression_tokens(container: SyncContainer) -> None:
    assert_type(container.get(Repository | None), Repository | None)
    assert_type(container.get(RepositorySelector), RepositorySelector)
    assert_type(qualified(Repository | None, "optional"), tuple[TypeForm[Repository | None], Hashable])
    assert_type(qualified(RepositorySelector, "selector"), tuple[TypeForm[RepositorySelector], Hashable])
    with container.override({qualified(RepositorySelector, "selector"): lambda _: Repository()}):
        assert_type(container.get(RepositorySelector, qualifier="selector"), RepositorySelector)


async def check_async_type_expression_tokens(container: AsyncContainer) -> None:
    assert_type(await container.get(Repository | None), Repository | None)
    assert_type(await container.get(RepositorySelector), RepositorySelector)
