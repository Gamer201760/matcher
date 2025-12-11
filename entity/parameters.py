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

    def to_dict(self) -> dict:
        return {
            'name': self.name,
            'surname': self.surname,
            'geo': {
                'lat': self.geo.lat,
                'lon': self.geo.lon,
            },
            'address': self.address,
            'photos': self.photos,
            'budget': self.budget,
            'room_count': self.room_count,
            'roommates_count': self.roommates_count,
            'month': self.month,
            'age': self.age,
            'smoking': self.smoking,
            'alko': self.alko,
            'pet': self.pet,
            'sex': self.sex.name,
            'user_type': self.user_type.name,
            'description': self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Parameters':
        return cls(
            name=data['name'],
            surname=data['surname'],
            geo=Point(
                lat=data['geo']['lat'],
                lon=data['geo']['lon'],
            ),
            address=data['address'],
            photos=list(data['photos']),
            budget=int(data['budget']),
            room_count=int(data['room_count']),
            roommates_count=int(data['roommates_count']),
            month=int(data['month']),
            age=int(data['age']),
            smoking=bool(data['smoking']),
            alko=bool(data['alko']),
            pet=bool(data['pet']),
            sex=Sex[data['sex']],
            user_type=UserType[data['user_type']],
            description=data['description'],
        )
