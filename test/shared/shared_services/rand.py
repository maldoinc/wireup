from wireup import service


@service
class RandomService:
    def get_random(self) -> int:
        return 4
