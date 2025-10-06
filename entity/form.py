from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List
from uuid import UUID

from entity.point import Point


class Sex(Enum):
    MALE = 1
    FEMALE = 2


class UserType(Enum):
    STUDENT = 1
    WORKER = 2
    TOURIST = 3


@dataclass
class Form:
    id: UUID
    user_id: UUID
    name: str
    surname: str

    geo: Point
    photos: List[str]
    budget: int
    room_count: int
    roommates_count: int
    age: int
    smoking: bool
    alko: bool
    pet: bool
    sex: Sex
    user_type: UserType
    description: str

    active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
