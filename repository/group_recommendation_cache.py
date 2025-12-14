import json
from uuid import UUID

import redis

from entity.group import Group

GROUP_DEFAULT_KEY = 'group_default'


class CacheGroupRecommendationRepositoryRedis:
    def __init__(
        self,
        redis_client: redis.Redis,
        key_prefix: str = 'matcher',
    ) -> None:
        self._redis = redis_client
        self._key_prefix = key_prefix
        self._pipe = self._redis.pipeline(transaction=False)

    def _key(self, user_id: UUID | str) -> str:
        return f'{self._key_prefix}:{str(user_id)}'

    def execute(self, user_id: UUID) -> list[tuple[Group, float]]:
        raw = self._redis.get(self._key(user_id))
        if raw is None:
            raw = self._redis.get(self._key(GROUP_DEFAULT_KEY))

        data = json.loads(raw)
        result: list[tuple[Group, float]] = []
        for item in data:
            group = Group.from_dict(item['group'])
            score = float(item['score'])
            result.append((group, score))
        return result

    def add(self, user_id: UUID, value: list[tuple[Group, float]]) -> None:
        payload = [{'group': group.to_dict(), 'score': score} for group, score in value]
        raw = json.dumps(payload)
        self._pipe.set(self._key(user_id), raw)

    def add_default(self, value: list[tuple[Group, float]]) -> None:
        payload = [{'group': group.to_dict(), 'score': score} for group, score in value]
        raw = json.dumps(payload)
        self._pipe.set(self._key(GROUP_DEFAULT_KEY), raw)

    def commit(self) -> None:
        self._pipe.execute()
