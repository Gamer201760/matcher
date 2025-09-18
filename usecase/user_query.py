from typing import Protocol

from entity.user import User
from usecase.user_repository import UserRepositoryInterface


class UserQueryInterface(Protocol):
    def create(self, user: User) -> str: ...
    def get(self, id: str) -> User: ...
    def update(self, user: User) -> None: ...
    def delete(self, id: str) -> None: ...


class UserQuery:
    def __init__(self, user_repo: UserRepositoryInterface) -> None:
        self.user_repo = user_repo

    def create(self, user: User) -> str:
        return self.user_repo.create(user)

    def get(self, id: str) -> User:
        return self.user_repo.get(id)

    def update(self, user: User) -> None:
        return self.user_repo.update(user)

    def delete(self, id: str) -> None:
        return self.user_repo.delete(id)
