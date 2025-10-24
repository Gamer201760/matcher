from datetime import datetime
from uuid import UUID

import neo4j

from entity.group import Group, GroupRequest
from entity.parameters import Parameters, Sex, UserType
from entity.point import Point


def db_group_to_group(db_dict: dict, group_id: UUID) -> Group:
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


def db_request_to_group_request(db_dict: dict) -> GroupRequest:
    """
    Convert database dictionary to GroupRequest entity.

    Args:
        db_dict: Dictionary from database

    Returns:
        GroupRequest: GroupRequest entity
    """
    # Parse request ID - stored as UUID string property
    request_id = db_dict['id']
    if isinstance(request_id, str):
        request_id = UUID(request_id)

    # Parse user ID
    user_id = db_dict['user_id']
    if isinstance(user_id, str):
        user_id = UUID(user_id)

    # Parse group ID - remove 'g_' prefix if present
    group_id = db_dict['group_id']
    if isinstance(group_id, str):
        clean_group_id = (
            group_id.replace('g_', '', 1) if group_id.startswith('g_') else group_id
        )
        group_id = UUID(clean_group_id)

    created_at = datetime.now()  # TODO: refactor
    if isinstance(db_dict['timestamp'], neo4j.time.DateTime):
        created_at = db_dict['timestamp'].to_native()

    return GroupRequest(
        id=request_id,
        group_id=group_id,
        user_id=user_id,
        created_at=created_at,
    )
