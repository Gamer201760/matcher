from uuid import UUID

from entity.form import Form
from entity.group import Group
from usecase.interface import GroupRepository


class GroupQuery:
    def __init__(self, repo: GroupRepository):
        self.repo = repo

    def get(self, group_id: UUID) -> Group:
        return self.repo.get(group_id)

    def get_by_user_id(self, user_id: UUID) -> Group:
        return self.repo.get_by_user_id(user_id)

    def delete(self, owner_id: UUID) -> None:
        # TODO: Добавить каскадное удаление из группы всех участников
        self.repo.delete_by_owner_id(owner_id)

    def list_members(self, group_id: UUID) -> list[Form]:
        return self.repo.list_members(group_id)
