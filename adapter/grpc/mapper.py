from datetime import datetime
from uuid import UUID

from google.protobuf.timestamp_pb2 import Timestamp

import gen.matcher.matcher_pb2 as pb2
from entity.form import Form
from entity.group import Group, GroupRequest
from entity.parameters import Parameters, Point, Sex, UserType


def to_proto_sex(sex: Sex) -> pb2.Sex.ValueType:
    if sex == Sex.MALE:
        return pb2.Sex.SEX_MALE
    elif sex == Sex.FEMALE:
        return pb2.Sex.SEX_FEMALE
    else:
        return pb2.Sex.SEX_UNSPECIFIED


def from_proto_sex(proto_sex: pb2.Sex.ValueType) -> Sex:
    if proto_sex == pb2.Sex.SEX_MALE:
        return Sex.MALE
    elif proto_sex == pb2.Sex.SEX_FEMALE:
        return Sex.FEMALE
    else:
        raise ValueError('Unknown sex value')


def to_proto_user_type(user_type: UserType) -> pb2.UserType.ValueType:
    if user_type == UserType.STUDENT:
        return pb2.UserType.USER_TYPE_STUDENT
    elif user_type == UserType.WORKER:
        return pb2.UserType.USER_TYPE_WORKER
    elif user_type == UserType.TOURIST:
        return pb2.UserType.USER_TYPE_TOURIST
    else:
        return pb2.UserType.USER_TYPE_UNSPECIFIED


def from_proto_user_type(proto_user_type: pb2.UserType.ValueType) -> UserType:
    if proto_user_type == pb2.UserType.USER_TYPE_STUDENT:
        return UserType.STUDENT
    elif proto_user_type == pb2.UserType.USER_TYPE_WORKER:
        return UserType.WORKER
    elif proto_user_type == pb2.UserType.USER_TYPE_TOURIST:
        return UserType.TOURIST
    else:
        raise ValueError('Unknown user type value')


def datetime_to_timestamp(dt: datetime) -> Timestamp:
    timestamp = Timestamp()
    timestamp.FromDatetime(dt)
    return timestamp


def timestamp_to_datetime(timestamp: Timestamp) -> datetime:
    return datetime.fromtimestamp(timestamp.seconds + timestamp.nanos / 1e9)


def to_proto_parameters(params: Parameters) -> pb2.Parameters:
    return pb2.Parameters(
        name=params.name,
        surname=params.surname,
        geo=pb2.Point(lat=params.geo.lat, lon=params.geo.lon),
        photos=params.photos,
        budget=params.budget,
        room_count=params.room_count,
        roommates_count=params.roommates_count,
        age=params.age,
        month=params.month,
        smoking=params.smoking,
        alko=params.alko,
        pet=params.pet,
        sex=to_proto_sex(params.sex),
        user_type=to_proto_user_type(params.user_type),
        description=params.description,
    )


def from_proto_parameters(proto: pb2.Parameters) -> Parameters:
    return Parameters(
        name=proto.name,
        surname=proto.surname,
        geo=Point(lat=proto.geo.lat, lon=proto.geo.lon),
        photos=list(proto.photos),
        budget=proto.budget,
        room_count=proto.room_count,
        roommates_count=proto.roommates_count,
        month=proto.month,
        age=proto.age,
        smoking=proto.smoking,
        alko=proto.alko,
        pet=proto.pet,
        sex=from_proto_sex(proto.sex),
        user_type=from_proto_user_type(proto.user_type),
        description=proto.description,
    )


def to_proto_form(form: Form) -> pb2.Form:
    return pb2.Form(
        id=str(form.id),
        user_id=str(form.user_id),
        parameters=to_proto_parameters(form.parameters),
        active=form.active,
        created_at=datetime_to_timestamp(form.created_at),
        updated_at=datetime_to_timestamp(form.updated_at),
    )


def to_proto_request(request: GroupRequest) -> pb2.GroupRequest:
    return pb2.GroupRequest(
        id=str(request.id),
        group_id=str(request.id),
        user_id=str(request.user_id),
        created_at=datetime_to_timestamp(request.created_at),
    )


def from_proto_form(proto: pb2.Form) -> Form:
    return Form(
        id=UUID(proto.id),
        user_id=UUID(proto.user_id),
        parameters=from_proto_parameters(proto.parameters),
        active=proto.active,
        created_at=timestamp_to_datetime(proto.created_at),
        updated_at=timestamp_to_datetime(proto.updated_at),
    )


def to_proto_group(group: Group) -> pb2.Group:
    return pb2.Group(
        id=str(group.id),
        owner_id=str(group.owner_id),
        parameters=to_proto_parameters(group.parameters),
        max_users=group.max_users,
        created_at=datetime_to_timestamp(group.created_at),
        updated_at=datetime_to_timestamp(group.updated_at),
    )


def to_proto_group_with_score(group: Group, score: float) -> pb2.GroupWithScore:
    return pb2.GroupWithScore(
        group=pb2.Group(
            id=str(group.id),
            owner_id=str(group.owner_id),
            parameters=to_proto_parameters(group.parameters),
            max_users=group.max_users,
            created_at=datetime_to_timestamp(group.created_at),
            updated_at=datetime_to_timestamp(group.updated_at),
        ),
        score=score,
    )


def from_proto_group(proto: pb2.Group) -> Group:
    return Group(
        id=UUID(proto.id),
        owner_id=UUID(proto.owner_id),
        parameters=from_proto_parameters(proto.parameters),
        max_users=proto.max_users,
        created_at=timestamp_to_datetime(proto.created_at),
        updated_at=timestamp_to_datetime(proto.updated_at),
    )
