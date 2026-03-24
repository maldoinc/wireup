from wireup import injectable


@injectable
class AsyncRandomService:
    async def get_random(self) -> int:
        return 4
