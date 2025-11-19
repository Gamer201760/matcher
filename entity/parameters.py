from dataclasses import dataclass
from enum import Enum

from entity.point import Point


class Sex(Enum):
    MALE = 1
    FEMALE = 2


class UserType(Enum):
    STUDENT = 1
    WORKER = 2
    TOURIST = 3


@dataclass
class Parameters:
    name: str
    surname: str
    geo: Point
    address: str
    photos: list[str]
    budget: int
    room_count: int
    roommates_count: int
    month: int
    age: int
    smoking: bool
    alko: bool
    pet: bool
    sex: Sex
    user_type: UserType
    description: str
