from typing import List, Protocol, Tuple
from uuid import UUID

from entity.errors import DomainError, NotFoundError
from entity.group import Group, GroupRequest

from .interface import (
    GroupRecomendationRepository,
    GroupRepository,
    GroupRequestRepository,
    NotificationRepository,
)


class FindGroupServiceInterface(Protocol):
    def execute(self, user_id: UUID) -> List[Tuple[Group, float]]: ...


class FindGroupService:
    def __init__(
        self,
        group_repo: GroupRepository,
        recommendation_repo: GroupRecomendationRepository,
    ):
        self._group_repo = group_repo
        self._recommendation_repo = recommendation_repo

    def execute(self, user_id: UUID) -> List[Tuple[Group, float]]:
        """
        Выполняет поиск подходящих групп для текущей группы пользователя.
        """
        # Находим группу, в которой состоит пользователь, чтобы дать рекомендации для неё.
        user_group = self._group_repo.get_by_user_id(user_id)
        # Делегируем логику поиска специализированному репозиторию.
        recommended_groups = self._recommendation_repo.execute(user_group.id)

        return recommended_groups


class GroupService:
    def __init__(
        self,
        group_repo: GroupRepository,
        request_repo: GroupRequestRepository,
        notify_repo: NotificationRepository,
    ):
        self._group_repo = group_repo
        self._request_repo = request_repo
        self._notify = notify_repo

    def get_requests(self, group_id: UUID) -> list[GroupRequest]:
        return self._request_repo.get_all_by_group_id(group_id)

    def get_requests_by_user_id(self, user_id: UUID) -> list[GroupRequest]:
        return self._request_repo.get_all_by_user_id(user_id)

    def send_join_request(self, user_id: UUID, group_id: UUID):
        """Пользователь отправляет запрос на вступление в группу."""
        if group_id in [
            i.group_id for i in self._request_repo.get_all_by_user_id(user_id)
        ]:
            raise DomainError(
                'Вы не можете отправить больше одной заявки на вступление в эту группу'
            )
        group = self._group_repo.get(group_id)
        if user_id in [i.user_id for i in self._group_repo.list_members(group_id)]:
            raise DomainError(
                'Вы не можете отправить заявку на вступление в свою же группу'
            )

        if self._group_repo.count_members(group_id) == group.max_users:
            raise DomainError('В этой группу уже максимум человек')

        self._request_repo.create(group_id, user_id)
        self._notify.send_join_request(group, user_id)
        self._notify.flush()

    def accept_join_request(self, owner_id: UUID, request_id: UUID):
        """
        Владелец группы ПРИНИМАЕТ запрос на вступление.
        При этом старая группа принятого пользователя удаляется.
        """
        try:
            group = self._group_repo.get_by_owner_id(owner_id)
        except NotFoundError:
            self.reject_join_request(owner_id, request_id)
            raise DomainError(
                'Только владелец может принимать запросы на вступление в группу'
            )

        request = self._request_repo.get(request_id)

        if self._group_repo.count_members(group.id) >= group.max_users:
            raise DomainError('Не удалось добавить пользователя: группа уже заполнена.')

        self._group_repo.delete_by_owner_id(request.user_id)
        self._group_repo.add_user(request.user_id, group.id)
        self._group_repo.calculate_params(group.id)
        self._request_repo.delete_all_by_user_id(request.user_id)
        self._notify.accept_join_request(group, request)
        self._notify.flush()

    def reject_join_request(self, owner_id: UUID, request_id: UUID):
        """Владелец группы ОТКЛОНЯЕТ запрос на вступление."""
        try:
            group = self._group_repo.get_by_owner_id(owner_id)
            request = self._request_repo.get(request_id)
            if group.id == request.group_id:
                self._request_repo.delete(request_id)
            else:
                raise DomainError('Этот запрос на вступленние не в вашу группу')
        except NotFoundError:
            raise DomainError('Только владелец группы может отклонять запросы')

        self._notify.reject_join_request(group, request)
        self._notify.flush()
