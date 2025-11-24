from uuid import UUID

from entity.errors import DomainError, NotFoundError
from entity.form import Form
from entity.group import Group
from usecase.interface import FormRepository, GroupRepository


class GroupQuery:
    def __init__(self, group_repo: GroupRepository, form_repo: FormRepository):
        self._group_repo = group_repo
        self._form_repo = form_repo

    def kick(self, owner_id: UUID, user_id: UUID):
        if owner_id == user_id:
            raise DomainError('Вы не можете выгнать самого себя')
        try:
            group = self._group_repo.get_by_owner_id(owner_id)
        except NotFoundError:
            raise DomainError('У вас нет прав выгнать человека из группы')
        self._group_repo.rm_user(user_id, group.id)
        self._group_repo.calculate_params(group.id)
        self._create_group(user_id)

    def leave(self, user_id: UUID):
        try:
            group = self._group_repo.get_by_user_id(user_id)
        except NotFoundError:
            raise DomainError('У вас группы')
        members = self._group_repo.list_members(group.id)
        if len(members) == 1:
            raise DomainError('Вы не можете выйти из группы, когда остались только вы')
        if group.owner_id == user_id:
            self._group_repo.change_owner(
                group.id, [x.user_id for x in members if x.user_id != user_id][0]
            )
        self._group_repo.rm_user(user_id, group.id)
        self._group_repo.calculate_params(group.id)
        self._create_group(user_id)

    def _create_group(self, user_id: UUID) -> None:
        form = self._form_repo.get_by_user_id(user_id)
        group_id = self._group_repo.create(
            Group(
                owner_id=user_id,
                parameters=form.parameters,
                max_users=form.parameters.roommates_count + 1,
            )
        )
        self._group_repo.add_user(user_id=user_id, group_id=group_id)
        self._group_repo.calculate_params(group_id)

    def get(self, group_id: UUID) -> Group:
        return self._group_repo.get(group_id)

    def get_by_user_id(self, user_id: UUID) -> Group:
        return self._group_repo.get_by_user_id(user_id)

    def delete(self, owner_id: UUID) -> None:
        # TODO: Добавить каскадное удаление из группы всех участников
        self._group_repo.delete_by_owner_id(owner_id)

    def list_members(self, group_id: UUID) -> list[Form]:
        return self._group_repo.list_members(group_id)
