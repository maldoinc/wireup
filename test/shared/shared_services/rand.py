from wireup import injectable


@injectable
class RandomService:
    def get_random(self) -> int:
        return 4
