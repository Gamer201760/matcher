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

    def get_all_by_group_id(self, group_id: UUID) -> list[GroupRequest]:
        return [r for r in self._storage.values() if r.group_id == group_id]

    def get_all_by_user_id(self, user_id: UUID) -> list[GroupRequest]:
        return [r for r in self._storage.values() if r.user_id == user_id]

    def delete(self, request_id: UUID) -> None:
        if request_id not in self._storage:
            raise NotFoundError(f'Запрос {request_id} не найден')
        del self._storage[request_id]

    def delete_all_by_user_id(self, user_id: UUID) -> None:
        to_delete = [rid for rid, r in self._storage.items() if r.user_id == user_id]
        for rid in to_delete:
            del self._storage[rid]
