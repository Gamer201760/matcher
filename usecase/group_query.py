from uuid import UUID

from entity.errors import DomainError, NotFoundError
from entity.form import Form
from entity.group import Group
from usecase.interface import GroupRepository


class GroupQuery:
    def __init__(self, repo: GroupRepository):
        self.repo = repo

    def kick(self, owner_id: UUID, user_id: UUID):
        try:
            group = self.repo.get_by_owner_id(owner_id)
        except NotFoundError:
            raise DomainError('У вас нет прав выгнать человека из группы')
        self.repo.rm_user(user_id, group.id)

    def leave(self, user_id: UUID):
        try:
            group = self.repo.get_by_user_id(user_id)
        except NotFoundError:
            raise DomainError('У вас группы')
        self.repo.rm_user(user_id, group.id)

    def get(self, group_id: UUID) -> Group:
        return self.repo.get(group_id)

    def get_by_user_id(self, user_id: UUID) -> Group:
        return self.repo.get_by_user_id(user_id)

    def delete(self, owner_id: UUID) -> None:
        # TODO: Добавить каскадное удаление из группы всех участников
        self.repo.delete_by_owner_id(owner_id)

    def list_members(self, group_id: UUID) -> list[Form]:
        return self.repo.list_members(group_id)
