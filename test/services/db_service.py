from dataclasses import dataclass


@dataclass
class DbService:
    connection_str: str
    cache_dir: str

    def get_result(self) -> str:
        return f"Querying {self.connection_str}; Caching results in {self.cache_dir}"
