from uuid import UUID, uuid4

from entity.errors import DomainError, NotFoundError
from entity.form import Form
from entity.group import Group
from entity.parameters import Parameters

from .interface import FormRepository, GroupRepository


class FormService:
    """
    Use Case для управления анкетой пользователя (CRUD).
    Предполагает, что репозитории берут на себя ответственность
    за проверку уникальности и идемпотентность удаления.
    """

    def __init__(self, form_repo: FormRepository, group_repo: GroupRepository):
        self._form_repo = form_repo
        self._group_repo = group_repo

    def create(self, user_id: UUID, parameters: Parameters) -> None:
        """
        Создает новую анкету и связанную с ней персональную группу для пользователя.

        Контракт:
        - Репозиторий `FormRepository` должен вызывать `EntityAlreadyExistsError`,
          если анкета для `form.user_id` уже существует.

        :param form: Объект анкеты с данными.
        :raises EntityAlreadyExistsError: Если у пользователя уже есть анкета.
        """
        self._form_repo.create(
            Form(
                id=uuid4(),
                user_id=user_id,
                parameters=parameters,
            )
        )

        group_id = self._group_repo.create(
            Group(
                id=uuid4(),
                max_users=parameters.roommates_count + 1,
                owner_id=user_id,
                parameters=parameters,
            )
        )

        self._group_repo.add_user(user_id=user_id, group_id=group_id)
        self._group_repo.calculate_params(group_id)

    def get_by_user(self, user_id: UUID) -> Form:
        """
        Получает анкету по ID пользователя.

        :param user_id: ID пользователя.
        :return: Объект Form.
        :raises NotFoundError: Если анкета не найдена (ответственность репозитория).
        """
        return self._form_repo.get_by_user_id(user_id)

    def update(self, user_id: UUID, parameters: Parameters) -> None:
        """
        Обновляет анкету пользователя и, при необходимости, его группу.

        Контракт:
        - Репозитории `get_by_user_id` должны вызывать `NotFoundError`, если
          сущности не найдены, т.к. нельзя обновить то, чего не существует.

        :param user_id: ID пользователя, чья анкета обновляется.
        :param parameters: Объект Parameters с новыми данными.
        :raises NotFoundError: Если анкета или группа пользователя не найдены.
        """
        try:
            # TODO: начало транзакции
            self._form_repo.update_parameters_by_user_id(user_id, parameters)
            group = self._group_repo.get_by_owner_id(user_id)
            if self._group_repo.count_members(group.id) == 1:
                self._group_repo.update_parameters(group.id, parameters)
                self._group_repo.calculate_params(group.id)
            # TODO: конец транзакции

        except NotFoundError:
            raise DomainError(
                'Вы не можете обновить анкету, пока состоите в группе, где больше одного участника'
            )

    def delete(self, user_id: UUID) -> None:
        """
        Удаляет анкету пользователя и его персональную группу.

        :param user_id: ID пользователя для удаления.
        """

        # TODO: начало транзакции
        group = self._group_repo.get_by_user_id(user_id)
        members = self._group_repo.list_members(group.id)
        if len(members) == 0:
            raise DomainError('Количество участников группы равно 0')

        if len(members) > 1:
            self._group_repo.rm_user(user_id, group.id)
            if group.owner_id == user_id:
                self._group_repo.change_owner(group.id, members[-1].user_id)
            self._group_repo.calculate_params(group.id)

        self._form_repo.delete_by_user_id(user_id)
        if len(members) == 1 and group.owner_id == user_id:
            self._group_repo.delete_by_owner_id(user_id)
        # TODO: конец транзакции
