from uuid import UUID

from entity.errors import EntityAlreadyExistsError, NotFoundError
from entity.form import Form
from usecase.interface import FormRepository


class FormQuery:
    def __init__(self, repo: FormRepository):
        self.repo = repo

    def create_form(self, form: Form) -> None:
        existing = self.repo.get_form_by_user(form.user_id)
        if existing:
            raise EntityAlreadyExistsError(f'User {form.user_id} already has a form')
        self.repo.create_form(form)

    def get_form(self, user_id: UUID) -> Form:
        form = self.repo.get_form_by_user(user_id)
        if not form:
            raise NotFoundError(f'Form for user {user_id} not found')
        return form

    def update_form(self, form: Form) -> None:
        existing = self.repo.get_form_by_user(form.user_id)
        if not existing:
            raise NotFoundError(f'Form for user {form.user_id} not found')
        self.repo.update_form(form)

    def delete_form(self, user_id: UUID) -> None:
        existing = self.repo.get_form_by_user(user_id)
        if not existing:
            raise NotFoundError(f'Form for user {user_id} not found')
        self.repo.delete_form_by_user(user_id)
