class RandomService:
    def __init__(self, num: int) -> None:
        self.num = num

    def get_random(self) -> int:
        return self.num
