from uuid import UUID, uuid4

from interface import FormRepository, GroupRepository

from entity.form import Form
from entity.group import Group

# ... (Код FindGroupsUseCase и GroupInteractionUseCase остается без изменений) ...


class FormUseCase:
    """
    Use Case для управления анкетой пользователя (CRUD).
    Предполагает, что репозитории берут на себя ответственность
    за проверку уникальности и идемпотентность удаления.
    """

    def __init__(self, form_repo: FormRepository, group_repo: GroupRepository):
        self._form_repo = form_repo
        self._group_repo = group_repo

    def create_form(self, form: Form) -> None:
        """
        Создает новую анкету и связанную с ней персональную группу для пользователя.

        Контракт:
        - Репозиторий `FormRepository` должен вызывать `EntityAlreadyExistsError`,
          если анкета для `form.user_id` уже существует.

        :param form: Объект анкеты с данными.
        :raises EntityAlreadyExistsError: Если у пользователя уже есть анкета.
        """
        # 1. Создаем анкету. Ответственность за проверку уникальности лежит на репозитории.
        self._form_repo.create(form)

        # 2. Создаем персональную группу для этого пользователя.
        new_group = Group(
            id=uuid4(),  # ID будет присвоен реализацией репозитория.
            max_users=form.roommates_count + 1,
            owner_id=form.user_id,
        )
        new_group_id = self._group_repo.create(new_group)

        # 3. Добавляем самого пользователя в его только что созданную группу.
        self._group_repo.add_user(user_id=form.user_id, group_id=new_group_id)

    def get_form_by_user(self, user_id: UUID) -> Form:
        """
        Получает анкету по ID пользователя.

        :param user_id: ID пользователя.
        :return: Объект Form.
        :raises NotFoundError: Если анкета не найдена (ответственность репозитория).
        """
        return self._form_repo.get_by_user_id(user_id)

    def update_form(self, user_id: UUID, updated_form_data: Form) -> None:
        """
        Обновляет анкету пользователя и, при необходимости, его группу.

        Контракт:
        - Репозитории `get_by_user_id` должны вызывать `NotFoundError`, если
          сущности не найдены, т.к. нельзя обновить то, чего не существует.

        :param user_id: ID пользователя, чья анкета обновляется.
        :param updated_form_data: Объект Form с новыми данными.
        :raises NotFoundError: Если анкета или группа пользователя не найдены.
        """
        self._form_repo.update_by_user_id(user_id, updated_form_data)

    def delete_form(self, user_id: UUID) -> None:
        """
        Удаляет анкету пользователя и его персональную группу.

        Контракт:
        - Репозитории `delete_by_owner_id` и `delete_by_user_id` должны быть
          идемпотентными, т.е. не вызывать ошибку, если сущность не найдена.

        :param user_id: ID пользователя для удаления.
        """
        # 1. Удаляем группу. Репозиторий не должен вызывать ошибку, если группы нет.
        self._group_repo.delete_by_owner_id(user_id)

        # 2. Удаляем анкету. Репозиторий не должен вызывать ошибку, если анкеты нет.
        self._form_repo.delete_by_user_id(user_id)
