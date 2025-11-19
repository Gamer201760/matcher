from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from entity.parameters import Parameters


@dataclass
class GroupRequest:
    id: UUID
    group_id: UUID
    user_id: UUID

    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class Group:
    owner_id: UUID
    parameters: Parameters
    max_users: int  # С учётом владельца группы
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def update_timestamp(self):
        self.updated_at = datetime.now(UTC)
