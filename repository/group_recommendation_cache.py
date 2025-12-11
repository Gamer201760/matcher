from uuid import UUID

from entity.group import Group


class CacheGroupRecomendationRepositoryRedis:
    def execute(self, user_id: UUID) -> list[tuple[Group, float]]: ...
    def add(self, user_id: UUID, value: list[tuple[Group, float]]) -> None: ...
