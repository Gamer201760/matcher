"""
Join request operations for Neo4j database.

This module handles:
- Join request creation
- Join request approval
- Request querying
"""

from ..logging_utils import setup_logger
from .group_ops import add_user_to_group, get_group_info

# Setup logger
logger = setup_logger('roommate_db', 'INFO')


def send_join_request(session, user_id, group_id):
    """
    Create a join request from a user to a group.

    Args:
        session: Neo4j session
        user_id: User ID sending the request
        group_id: Target group ID
    """
    request_query = """
        MATCH (u:User {id: $user_id})
        MATCH (g:Group {id: $group_id})
        MERGE (u)-[r:JOIN_REQUEST]->(g)
        SET r.timestamp = datetime()
        RETURN r
    """
    session.run(request_query, user_id=user_id, group_id=group_id)
    logger.info(f'✓ User {user_id} sent join request to group {group_id}')


def approve_join_request(
    session,
    group_member_user_id,
    user_id,
    max_roommates,
    caps=None,
    use_weights=False,
    weights=None,
):
    """
    Approve a user's join request and add them to the group.

    Args:
        session: Neo4j session
        group_member_user_id: User who is approving (must be in the target group)
        user_id: User being approved
        max_roommates: Maximum members allowed before group becomes inactive
        caps: Normalization caps
        use_weights: Whether to use weighted vectors
        weights: Parameter weights

    Returns:
        bool: True if successful, False otherwise

    Raises:
        ValueError: If approver is not in a group or no request exists
    """
    # Get the approver's group
    group_query = """
        MATCH (approver:User {id: $group_member_user_id})-[:MEMBER_OF]->(g:Group)
        RETURN g.id as group_id
    """
    result = session.run(group_query, group_member_user_id=group_member_user_id)
    record = result.single()

    if not record:
        raise ValueError(f'User {group_member_user_id} is not in any group')

    target_group_id = record['group_id']

    # Check if join request exists
    check_request_query = """
        MATCH (u:User {id: $user_id})-[r:JOIN_REQUEST]->(g:Group {id: $group_id})
        RETURN r
    """
    request_result = session.run(
        check_request_query, user_id=user_id, group_id=target_group_id
    )

    if not request_result.single():
        raise ValueError(
            f'No join request found from user {user_id} to group {target_group_id}'
        )

    # Add user to group
    success = add_user_to_group(
        session, user_id, target_group_id, caps, use_weights, weights
    )

    if not success:
        return False

    # Delete the join request
    delete_request_query = """
        MATCH (u:User {id: $user_id})-[r:JOIN_REQUEST]->(g:Group {id: $group_id})
        DELETE r
    """
    session.run(delete_request_query, user_id=user_id, group_id=target_group_id)

    # Check if group is full and mark as inactive if needed
    group_info = get_group_info(session, target_group_id)
    if group_info and group_info['member_count'] >= max_roommates:
        inactive_query = """
            MATCH (g:Group {id: $group_id})
            SET g.active = false
        """
        session.run(inactive_query, group_id=target_group_id)
        logger.info(
            f'✓ Group {target_group_id} marked as inactive (reached max capacity)'
        )

    logger.info(f'✓ User {user_id} approved and added to group {target_group_id}')
    return True


# New helper functions for repository implementations


def get_join_request(session, request_id):
    """
    Get a single join request by ID.

    Args:
        session: Neo4j session
        request_id: Request ID (UUID stored as property)

    Returns:
        dict: Request data with id, user_id, group_id, timestamp or None

    Note: Looks up by request_id property instead of internal Neo4j ID.
    """
    query = """
        MATCH (u:User)-[r:JOIN_REQUEST]->(g:Group)
        WHERE r.request_id = $request_id
        RETURN r.request_id as id, u.id as user_id, g.id as group_id, r.timestamp as timestamp
    """
    result = session.run(query, request_id=str(request_id))
    record = result.single()

    if not record:
        return None

    return {
        'id': str(record['id']),
        'user_id': record['user_id'],
        'group_id': record['group_id'],
        'timestamp': record['timestamp'],
    }


def get_all_join_requests(session, group_id):
    """
    Get all join requests for a specific group.

    Args:
        session: Neo4j session
        group_id: Group ID

    Returns:
        list: List of request dicts with id, user_id, group_id, timestamp

    Note: Returns request_id property stored on the relationship.
    """
    query = """
        MATCH (u:User)-[r:JOIN_REQUEST]->(g:Group {id: $group_id})
        RETURN r.request_id as id, u.id as user_id, g.id as group_id, r.timestamp as timestamp
        ORDER BY r.timestamp DESC
    """
    result = session.run(query, group_id=group_id)

    requests = []
    for record in result:
        requests.append(
            {
                'id': str(record['id']),
                'user_id': record['user_id'],
                'group_id': record['group_id'],
                'timestamp': record['timestamp'],
            }
        )

    return requests


def delete_join_request(session, request_id):
    """
    Delete a join request by its ID.

    Args:
        session: Neo4j session
        request_id: Request ID (UUID property)

    Note: Deletes by request_id property stored on the relationship.
    """
    query = """
        MATCH ()-[r:JOIN_REQUEST]->()
        WHERE r.request_id = $request_id
        DELETE r
    """
    session.run(query, request_id=str(request_id))
    logger.info(f'✓ Deleted join request {request_id}')


def create_join_request_with_id(session, request_id, user_id, group_id):
    """
    Create a join request with a specific ID (for testing/migration purposes).

    Args:
        session: Neo4j session
        request_id: String UUID for the request
        user_id: String User ID sending the request
        group_id: String Target group ID

    Note: Neo4j doesn't allow setting relationship IDs directly, so we store
    the UUID as a property instead. All IDs should be passed as strings.
    """
    request_query = """
        MATCH (u:User {id: $user_id})
        MATCH (g:Group {id: $group_id})
        CREATE (u)-[r:JOIN_REQUEST {request_id: $request_id, timestamp: datetime()}]->(g)
        RETURN r
    """
    session.run(
        request_query, request_id=request_id, user_id=user_id, group_id=group_id
    )
    logger.info(
        f'✓ Created join request {request_id} from user {user_id} to group {group_id}'
    )
