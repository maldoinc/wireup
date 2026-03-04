from wireup import injectable


class AsyncDependency: ...


@injectable
async def make_async_dependency() -> AsyncDependency:
    return AsyncDependency()
