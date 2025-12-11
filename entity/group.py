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

    def to_dict(self) -> dict:
        return {
            'id': str(self.id),
            'group_id': str(self.group_id),
            'user_id': str(self.user_id),
            'created_at': self.created_at.isoformat(),
        }


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

    def to_dict(self) -> dict:
        return {
            'id': str(self.id),
            'owner_id': str(self.owner_id),
            'parameters': self.parameters.to_dict(),
            'max_users': self.max_users,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Group':
        return cls(
            id=UUID(data['id']),
            owner_id=UUID(data['owner_id']),
            parameters=Parameters.from_dict(data['parameters']),
            max_users=int(data['max_users']),
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
        )
