from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from entity.parameters import Parameters


@dataclass
class Form:
    id: UUID
    user_id: UUID

    parameters: Parameters

    active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
