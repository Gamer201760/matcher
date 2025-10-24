from uuid import UUID

from entity.group import Group
from entity.parameters import Parameters, Sex, UserType
from entity.point import Point


def db_dict_to_group(db_dict: dict, group_id: UUID) -> Group:
    """
    Convert database dictionary to Group entity.

    Args:
        db_dict: Dictionary from database
        group_id: Group ID

    Returns:
        Group: Group entity
    """
    # Extract parameters
    params_dict = db_dict.get('parameters', {})

    parameters = Parameters(
        name=db_dict.get('name', ''),
        surname='',
        geo=Point(0.0, 0.0),
        photos=[],
        budget=params_dict.get('budget', 0),
        room_count=params_dict.get('rooms', 0),
        roommates_count=params_dict.get('roommates', 0),
        age=0,
        smoking=False,
        alko=False,
        pet=False,
        sex=Sex.MALE,
        user_type=UserType.STUDENT,
        description='',
    )

    # Extract owner_id - in current impl, first member is typically owner
    members = db_dict.get('members', [])
    owner_id = UUID(members[0]['id']) if members else group_id

    # Extract max_users from roommates parameter
    max_users = params_dict.get('roommates', 4)

    return Group(
        id=group_id,
        owner_id=owner_id,
        parameters=parameters,
        max_users=int(max_users),
    )
