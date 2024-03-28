from test.unit.services.no_annotations.random.random_service import RandomService


class TrulyRandomService:
    def __init__(self, random_service: RandomService) -> None:
        self.random_service = random_service

    def get_truly_random(self):
        return self.random_service.get_random() + 1
