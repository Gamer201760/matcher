from typing import List
from uuid import UUID

from interface import (
    GroupRecomendationRepository,
    GroupRepository,
    NotificationService,
)

from entity.errors import DomainError
from entity.group import Group


class FindGroupsUseCase:
    def __init__(
        self,
        group_repo: GroupRepository,
        recommendation_repo: GroupRecomendationRepository,
    ):
        self._group_repo = group_repo
        self._recommendation_repo = recommendation_repo

    def execute(self, user_id: UUID) -> List[Group]:
        """
        Выполняет поиск подходящих групп для текущей группы пользователя.
        """
        # Находим группу, в которой состоит пользователь, чтобы дать рекомендации для неё.
        user_group = self._group_repo.get_by_user_id(user_id)
        # Делегируем логику поиска специализированному репозиторию.
        recommended_groups = self._recommendation_repo.execute(user_group.id)

        return recommended_groups


class GroupInteractionUseCase:
    def __init__(
        self,
        group_repo: GroupRepository,
        notifier: NotificationService,
    ):
        self._group_repo = group_repo
        self._notifier = notifier

    def send_join_request(self, requester_user_id: UUID, target_group_id: UUID):
        """Пользователь отправляет запрос на вступление в группу."""
        target_group = self._group_repo.get(target_group_id)

        # Проверяем, есть ли в группе свободное место
        if self._group_repo.count_members(target_group_id) == target_group.max_users:
            raise DomainError('В этой группу уже максимум человек')

        # Уведомляем владельца группы
        self._notifier.notify_owner_of_new_request(
            group_id=target_group.id,
            user_id=requester_user_id,
        )

    def accept_join_request(
        self, owner_user_id: UUID, requester_user_id: UUID, group_id: UUID
    ):
        """
        Владелец группы ПРИНИМАЕТ запрос на вступление.
        При этом старая группа принятого пользователя удаляется.
        """
        target_group = self._group_repo.get(group_id)
        # 1. Проверка прав: является ли пользователь владельцем группы
        if target_group.owner_id != owner_user_id:
            raise DomainError('Только владелец группы может принимать участников.')

        # 2. Проверка наличия места
        count_members = self._group_repo.count_members(group_id)
        if count_members >= target_group.max_users:
            # Если место уже заняли, автоматически отклоняем
            self.reject_join_request(owner_user_id, requester_user_id, group_id)
            raise DomainError('Не удалось добавить пользователя: группа уже заполнена.')

        # Начало транзакции
        # 3. Удаление старой группы пользователя
        # Находим старую группу пользователя, чтобы её удалить.
        # Мы ожидаем, что пользователь-одиночка является владельцем своей группы.
        self._group_repo.delete_by_owner_id(requester_user_id)
        # 4. Добавление пользователя в новую группу
        self._group_repo.add_user(user_id=requester_user_id, group_id=group_id)
        # 5. Уведомление пользователя об успехе
        self._notifier.notify_user_of_decision(
            user_id=requester_user_id, group_id=group_id, accepted=True
        )
        # Конец транзакции

    def reject_join_request(
        self, owner_user_id: UUID, requester_user_id: UUID, group_id: UUID
    ):
        """Владелец группы ОТКЛОНЯЕТ запрос на вступление."""
        target_group = self._group_repo.get(group_id)

        # 1. Проверка прав: является ли пользователь владельцем группы
        if target_group.owner_id != owner_user_id:
            raise DomainError('Только владелец группы может отклонять запросы.')

        # 2. Уведомление пользователя об отказе
        self._notifier.notify_user_of_decision(
            user_id=requester_user_id, group_id=group_id, accepted=False
        )
