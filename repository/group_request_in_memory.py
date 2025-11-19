from uuid import UUID, uuid4

from entity.errors import NotFoundError
from entity.group import GroupRequest


class InMemoryGroupRequestRepository:
    def __init__(self) -> None:
        self._storage: dict[UUID, GroupRequest] = {}

    def create(self, group_id: UUID, user_id: UUID) -> UUID:
        request_id = uuid4()
        self._storage[request_id] = GroupRequest(
            id=request_id,
            group_id=group_id,
            user_id=user_id,
        )
        return request_id

    def get(self, request_id: UUID) -> GroupRequest:
        if request_id not in self._storage:
            raise NotFoundError(f'Запрос {request_id} не найден')
        return self._storage[request_id]

    def get_all(self, group_id: UUID) -> list[GroupRequest]:
        return [r for r in self._storage.values() if r.group_id == group_id]

    def delete(self, request_id: UUID) -> None:
        if request_id not in self._storage:
            raise NotFoundError(f'Запрос {request_id} не найден')
        del self._storage[request_id]
