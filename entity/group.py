from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from entity.parameters import Parameters


@dataclass
class GroupRequest:
    id: UUID
    group_id: UUID
    user_id: UUID

    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Group:
    id: UUID
    owner_id: UUID
    parameters: Parameters
    max_users: int  # С учётом владельца группы
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def update_timestamp(self):
        self.updated_at = datetime.utcnow()
