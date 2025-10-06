from typing import Dict
from uuid import UUID

from google.protobuf.timestamp_pb2 import Timestamp

from entity.form import Form, Sex, UserType
from entity.point import Point
from gen.form import form_pb2

domain_sex_to_proto: Dict[Sex, form_pb2.Sex.ValueType] = {
    Sex.FEMALE: form_pb2.Sex.FEMALE,
    Sex.MALE: form_pb2.Sex.MALE,
}
domain_user_type_to_proto: Dict[UserType, form_pb2.UserType.ValueType] = {
    UserType.STUDENT: form_pb2.UserType.STUDENT,
    UserType.WORKER: form_pb2.UserType.WORKER,
    UserType.TOURIST: form_pb2.UserType.TOURIST,
}


def proto_to_domain(form_proto: form_pb2.Form) -> Form:
    """
    Конвертирует Protobuf-сообщение Form в доменную модель Form (dataclass).
    """
    return Form(
        id=UUID(form_proto.id),
        user_id=UUID(form_proto.user_id),
        name=form_proto.name,
        surname=form_proto.surname,
        photos=list(form_proto.photos),
        budget=form_proto.budget,
        room_count=form_proto.room_count,
        roommates_count=form_proto.roommates_count,
        geo=Point(lat=form_proto.geo.lat, lon=form_proto.geo.lon),
        age=form_proto.age,
        smoking=form_proto.smoking,
        alko=form_proto.alko,
        pet=form_proto.pet,
        # Преобразуем int из proto в Enum доменной модели по значению
        sex=Sex(form_proto.sex),
        user_type=UserType(form_proto.user_type),
        description=form_proto.description,
        active=form_proto.active,
        # Используем встроенный метод для конвертации Timestamp -> datetime
        created_at=form_proto.created_at.ToDatetime(tzinfo=None),
        updated_at=form_proto.updated_at.ToDatetime(tzinfo=None),
    )


def domain_to_proto(form_domain: Form) -> form_pb2.Form:
    """
    Конвертирует доменную модель Form (dataclass) в Protobuf-сообщение Form.
    """
    # Конвертируем datetime в google.protobuf.Timestamp
    created_at_ts = Timestamp()
    created_at_ts.FromDatetime(form_domain.created_at)

    updated_at_ts = Timestamp()
    updated_at_ts.FromDatetime(form_domain.updated_at)

    form_pb2.Sex.FEMALE
    return form_pb2.Form(
        id=str(form_domain.id),
        user_id=str(form_domain.user_id),
        name=form_domain.name,
        surname=form_domain.surname,
        photos=form_domain.photos,
        budget=form_domain.budget,
        room_count=form_domain.room_count,
        roommates_count=form_domain.roommates_count,
        geo=form_pb2.Point(lat=form_domain.geo.lat, lon=form_domain.geo.lon),
        age=form_domain.age,
        smoking=form_domain.smoking,
        alko=form_domain.alko,
        pet=form_domain.pet,
        # Получаем int-значение из Enum доменной модели
        sex=domain_sex_to_proto[form_domain.sex],
        user_type=domain_user_type_to_proto[form_domain.user_type],
        description=form_domain.description,
        active=form_domain.active,
        created_at=created_at_ts,
        updated_at=updated_at_ts,
    )
