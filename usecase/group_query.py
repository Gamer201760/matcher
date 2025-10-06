from uuid import UUID

from entity.group import Group
from usecase.interface import GroupRepository


class GroupQuery:
    def __init__(self, repo: GroupRepository):
        self.repo = repo

    def create_group(self, group: Group) -> None:
        self.repo.create_group(group)

    def get_group(self, group_id: UUID) -> Group:
        return self.repo.get_group(group_id)

    def update_group(self, group: Group) -> None:
        group.update_timestamp()
        self.repo.update_group(group)

    def delete_group(self, group_id: UUID) -> None:
        self.repo.delete_group(group_id)

    def list_groups(self) -> list[Group]:
        return self.repo.list_groups()
