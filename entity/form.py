from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from entity.parameters import Parameters


@dataclass
class Form:
    user_id: UUID

    parameters: Parameters

    id: UUID = field(default_factory=uuid4)
    active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
