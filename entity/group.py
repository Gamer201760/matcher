from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass
class GroupMembers:
    group_id: UUID
    form_id: UUID


@dataclass
class Group:
    id: UUID
    owner_id: UUID
    max_users: int  # С учётом владельца группы
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def update_timestamp(self):
        self.updated_at = datetime.utcnow()
