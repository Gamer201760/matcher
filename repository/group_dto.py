from datetime import datetime
from logging import getLogger
from uuid import UUID, uuid4

import neo4j

from entity.group import Group, GroupRequest
from repository.form_dto import db_dict_to_parameters

logger = getLogger(__name__)


def db_group_to_group(db_dict: dict, group_id: UUID) -> Group:
    """
    Convert database dictionary to Group entity.

    Args:
        db_dict: Dictionary from database
        group_id: Group ID

    Returns:
        Group: Group entity
    """
    # Extract parameters from 'parameters' sub-dict (PARAMETERS fields)
    params_dict = db_dict.get('parameters', {})
    logger.debug(params_dict)

    # Merge PARAMETERS fields and metadata fields for DTO conversion
    # The db_dict already contains metadata fields from get_group_info
    # We need to add the PARAMETERS fields which are in the params_dict
    merged_dict = {
        **db_dict,  # Includes name, surname, geo_lat, geo_lon, photos, age, etc.
        'rooms': params_dict.get('rooms', 0),
        'roommates': params_dict.get('roommates', 0),
        'budget': params_dict.get('budget', 0),
        'months': params_dict.get('months', 0),
    }

    # Use centralized DTO function to convert to Parameters
    parameters = db_dict_to_parameters(merged_dict)

    # Extract owner_id - in current impl, first member is typically owner
    # Extract max_users from roommates parameter
    max_users = int(params_dict.get('roommates', 4))

    return Group(
        id=group_id,
        owner_id=UUID(db_dict.get('owner_id', uuid4())),
        parameters=parameters,
        max_users=max_users,
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

    # Parse group ID
    group_id = db_dict['group_id']
    if isinstance(group_id, str):
        group_id = UUID(group_id)

    created_at = datetime.now()  # TODO: refactor
    if isinstance(db_dict['timestamp'], neo4j.time.DateTime):
        created_at = db_dict['timestamp'].to_native()

    return GroupRequest(
        id=request_id,
        group_id=group_id,
        user_id=user_id,
        created_at=created_at,
    )
