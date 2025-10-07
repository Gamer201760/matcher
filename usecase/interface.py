from typing import List, Protocol
from uuid import UUID

from entity.form import Form
from entity.group import Group


class FormRepository(Protocol):
    def create(self, form: Form) -> None: ...
    def get_by_user_id(self, user_id: UUID) -> Form: ...
    def update_by_user_id(self, user_id: UUID, form: Form) -> None: ...
    def delete_by_user_id(self, user_id: UUID) -> None: ...


class GroupRepository(Protocol):
    def create(self, group: Group) -> UUID: ...
    def get(self, group_id: UUID) -> Group: ...
    def get_by_user_id(self, user_id: UUID) -> Group: ...
    def update(self, group: Group) -> None: ...
    def delete(self, group_id: UUID) -> None: ...
    def delete_by_owner_id(self, owner_id: UUID) -> None: ...

    def list_members(self, group_id: UUID) -> List[Form]: ...
    def count_members(self, group_id: UUID) -> int: ...
    def add_user(self, user_id: UUID, group_id: UUID) -> None: ...


class GroupRecomendationRepository(Protocol):
    """Рекомендует группу другой группе"""

    def execute(self, group_id: UUID) -> List[Group]:
        """
        Берёт среднюю из анкет пользователей, состоящих в группе
        и ищет ближайших из остальных групп, так же по средним из анкет
        """
        ...


class NotificationService(Protocol):
    """Абстракция для отправки уведомлений пользователям"""

    def notify_owner_of_new_request(
        self,
        group_id: UUID,
        user_id: UUID,
    ) -> None:
        """Уведомить владельца группы о новом запросе на вступление."""

    def notify_user_of_decision(
        self,
        user_id: UUID,
        group_id: UUID,
        accepted: bool,
    ) -> None:
        """Уведомить пользователя о решении (принят или отклонен)"""
