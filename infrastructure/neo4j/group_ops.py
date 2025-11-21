"""
Group operations for Neo4j database.

This module handles:
- Group CRUD operations
- Group membership management
- Group parameter calculations
- Member addition and removal
"""

from recommendation import create_vector

from ..config import GROUP_PARAMETER_WEIGHTS, PARAMETERS, get_parameter_statistics
from ..logging_utils import (
    log_neo4j_query,
    log_vector_operation,
    setup_logger,
)

# Setup logger
logger = setup_logger('roommate_db', 'INFO')


def add_user_to_group(session, user_id, group_id):
    """
    Create a MEMBER_OF relationship between a user and a group.

    Args:
        session: Neo4j session
        user_id: User ID
        group_id: ID of group
    """
    add_query = """
        MATCH (u:User {id: $user_id})
        MATCH (g:Group {id: $group_id})
        MERGE (u)-[:MEMBER_OF]->(g)
        RETURN u.id as user_id, g.id as group_id
    """

    log_neo4j_query(logger, add_query)
    result = session.run(add_query, user_id=user_id, group_id=group_id)
    record = result.single()

    if not record:
        logger.error(f'Failed to add user {user_id} to group {group_id}')
        return False

    logger.info(f'✓ User {user_id} added to group {group_id}')
    return True


def remove_user_from_group(session, user_id, group_id=None):
    """
    Remove a user from a group by unlinking the MEMBER_OF relationship.

    Args:
        session: Neo4j session
        user_id: ID of user to remove
        group_id: Optional group ID. If not provided, removes user from any group they're a member of.

    Returns:
        bool: True if relationship was deleted, False if user was not in the group

    Raises:
        ValueError: If user is not in a group (when group_id is None)
    """
    try:
        if group_id:
            # Remove from specific group
            delete_relationship_query = """
                MATCH (u:User {id: $user_id})-[r:MEMBER_OF]->(g:Group {id: $group_id})
                DELETE r
                RETURN g.id as group_id
            """
            log_neo4j_query(
                logger,
                delete_relationship_query,
                user_id=user_id,
                group_id=group_id,
            )
            result = session.run(
                delete_relationship_query,
                user_id=user_id,
                group_id=group_id,
            )
            record = result.single()

            if not record:
                logger.warning(
                    f'User {user_id} is not a member of group {group_id}'
                )
                return False

            logger.info(
                f'✓ Removed user {user_id} from group {group_id}'
            )
            return True
        else:
            # Remove from any group
            delete_relationship_query = """
                MATCH (u:User {id: $user_id})-[r:MEMBER_OF]->(g:Group)
                DELETE r
                RETURN g.id as group_id
            """
            log_neo4j_query(
                logger,
                delete_relationship_query,
                user_id=user_id,
            )
            result = session.run(
                delete_relationship_query,
                user_id=user_id,
            )
            record = result.single()

            if not record:
                logger.warning(f'User {user_id} is not a member of any group')
                raise ValueError(f'User {user_id} is not a member of any group')

            group_id = record['group_id']
            logger.info(
                f'✓ Removed user {user_id} from group {group_id}'
            )
            return True

    except ValueError:
        # Re-raise ValueError for proper error handling upstream
        raise
    except Exception as e:
        logger.error(f'Error removing user {user_id} from group: {e}')
        logger.debug(f'Error details: {type(e).__name__}: {str(e)}')
        raise RuntimeError(f'Failed to remove user {user_id} from group: {e}')


def get_group_info(session, group_id):
    """Get detailed information about a group including members and parameters."""
    query = """
        MATCH (g:Group {id: $group_id})
        OPTIONAL MATCH (g)-[:HAS_PARAMETER]->(gp:GroupParameter)
        OPTIONAL MATCH (u:User)-[:MEMBER_OF]->(g)
        RETURN g,
               collect(DISTINCT {name: gp.name, value: gp.value}) as parameters,
               collect(DISTINCT {id: u.id, name: u.name}) as members
    """
    result = session.run(query, group_id=group_id)
    record = result.single()

    if not record:
        return None

    group = record['g']
    parameters = {param['name']: param['value'] for param in record['parameters']}
    members = record['members']

    # Include metadata fields in the return dict for proper DTO conversion
    return {
        'id': group['id'],
        'name': group['name'],
        'surname': group.get('surname', ''),
        'geo_lat': group.get('geo_lat', 0.0),
        'geo_lon': group.get('geo_lon', 0.0),
        'address': group.get('address', ''),
        'photos': group.get('photos', []),
        'age': group.get('age', 0),
        'smoking': group.get('smoking', False),
        'alko': group.get('alko', False),
        'pet': group.get('pet', False),
        'sex': group.get('sex', 1),
        'user_type': group.get('user_type', 1),
        'description': group.get('description', ''),
        'parameters': parameters,
        'members': members,
        'member_count': len(members),
        'vector': group['embedding'],
    }


def get_group_with_status(session, group_id):
    """
    Get group information including active status and members.

    Args:
        session: Neo4j session
        group_id: Group ID

    Returns:
        dict: Group data with id, roommates, active, and member_ids
        None: If group not found
    """
    group_info = get_group_info(session, group_id)

    if not group_info:
        return None

    # Get active status
    active_query = """
        MATCH (g:Group {id: $group_id})
        RETURN coalesce(g.active, true) as active
    """
    result = session.run(active_query, group_id=group_id)
    record = result.single()
    active = record['active'] if record else True

    roommates_count = group_info['parameters'].get(
        'roommates', group_info['member_count']
    )
    member_ids = [member['id'] for member in group_info['members']]

    return {
        'id': group_info['id'],
        'roommates': int(roommates_count),
        'active': active,
        'member_ids': member_ids,
    }


def get_group_member_parameters(session, group_id, exclude_user_id=None):
    """Fetch parameter values for all members of a group, optionally excluding a user."""
    query = """
        MATCH (u:User)-[:MEMBER_OF]->(g:Group {id: $group_id})
        WHERE $exclude_user_id IS NULL OR u.id <> $exclude_user_id
        WITH u
        OPTIONAL MATCH (u)-[:HAS_PARAMETER]->(pr:Parameter {name: 'rooms'})
        OPTIONAL MATCH (u)-[:HAS_PARAMETER]->(pm:Parameter {name: 'roommates'})
        OPTIONAL MATCH (u)-[:HAS_PARAMETER]->(pb:Parameter {name: 'budget'})
        OPTIONAL MATCH (u)-[:HAS_PARAMETER]->(pn:Parameter {name: 'months'})
        OPTIONAL MATCH (u)-[:HAS_PARAMETER]->(pglat:Parameter {name: 'geo_lat'})
        OPTIONAL MATCH (u)-[:HAS_PARAMETER]->(pglon:Parameter {name: 'geo_lon'})
        OPTIONAL MATCH (u)-[:HAS_PARAMETER]->(pa:Parameter {name: 'age'})
        RETURN u.id as id,
               u.name as name,
               coalesce(pr.value, 0) as rooms,
               coalesce(pm.value, 0) as roommates,
               coalesce(pb.value, 0) as budget,
               coalesce(pn.value, 1) as months,
               coalesce(pglat.value, 0.0) as geo_lat,
               coalesce(pglon.value, 0.0) as geo_lon,
               coalesce(pa.value, 0) as age
    """
    result = session.run(query, group_id=group_id, exclude_user_id=exclude_user_id)
    return [r.data() for r in result]


# New helper functions for repository implementations


def get_group_by_user_id(session, user_id):
    """
    Get the group that a user is a member of.

    Args:
        session: Neo4j session
        user_id: User ID

    Returns:
        dict: Group info or None if user not in a group
    """
    query = """
        MATCH (u:User {id: $user_id})-[:MEMBER_OF]->(g:Group)
        RETURN g.id as group_id
    """
    result = session.run(query, user_id=user_id)
    record = result.single()

    if not record:
        return None

    return get_group_info(session, record['group_id'])


def get_group_by_owner_id(session, owner_id):
    """
    Get the group owned by a specific user.

    Args:
        session: Neo4j session
        owner_id: Owner user ID

    Returns:
        dict: Group info or None if no group found
    """
    query = """
        MATCH (g:Group)
        WHERE g.owner_id = $owner_id
        RETURN g.id as group_id
    """
    result = session.run(query, owner_id=owner_id)
    record = result.single()

    if not record:
        return None

    return get_group_info(session, record['group_id'])


def list_group_members(session, group_id):
    """
    List all members of a group as Form-like objects.

    Args:
        session: Neo4j session
        group_id: Group ID

    Returns:
        list: List of member info dicts with user_id and parameters
    """
    from .user_ops import get_user_form

    query = """
        MATCH (u:User)-[:MEMBER_OF]->(g:Group {id: $group_id})
        RETURN u.id as user_id
    """
    result = session.run(query, group_id=group_id)

    members = []
    for record in result:
        user_form = get_user_form(session, record['user_id'])
        if user_form:
            members.append(user_form)

    return members


def count_group_members(session, group_id):
    """
    Count the number of members in a group.

    Args:
        session: Neo4j session
        group_id: Group ID

    Returns:
        int: Number of members
    """
    query = """
        MATCH (u:User)-[:MEMBER_OF]->(g:Group {id: $group_id})
        RETURN count(u) as member_count
    """
    result = session.run(query, group_id=group_id)
    record = result.single()
    return record['member_count'] if record else 0


def update_group_parameters(
    session, group_id, parameters_dict, caps=None, use_weights=False, weights=None
):
    """
    Update group parameters and recalculate the group vector.

    Updates all parameters in parameters_dict on the Group node and GroupParameter nodes.
    Only PARAMETERS fields are used for vector calculation.

    Args:
        session: Neo4j session
        group_id: Group ID
        parameters_dict: Dict with parameter values (can include any Group property)
        caps: Normalization caps
        use_weights: Whether to use weighted vectors
        weights: Parameter weights
    """
    # Create new group vector (only using PARAMETERS fields)
    group_values = {p: parameters_dict.get(p, 0) for p in PARAMETERS}
    new_vector = create_vector(
        group_values,
        PARAMETERS,
        statistics=get_parameter_statistics(),
        weights=weights if use_weights else None,
    )

    # Build dynamic SET clauses for all parameters in parameters_dict
    set_clauses = []
    query_params = {'group_id': group_id, 'embedding': new_vector}
    
    for param_name, param_value in parameters_dict.items():
        # Skip embedding as it's handled separately
        if param_name == 'embedding':
            continue
        set_clauses.append(f'g.{param_name} = ${param_name}')
        query_params[param_name] = param_value
    
    # Build GroupParameter update - only update PARAMETERS that are in parameters_dict
    param_in_params = [p for p in PARAMETERS if p in parameters_dict]
    
    # Build SET clause for Group node - include all parameters + embedding
    all_set_clauses = set_clauses + ['g.embedding = $embedding']
    set_clause_str = ',\n            '.join(all_set_clauses)
    
    if param_in_params:
        case_clauses = [
            f"WHEN '{param}' THEN ${param}" for param in param_in_params
        ]
        case_clause_str = '\n                    '.join(case_clauses)
        update_query = f"""
        MATCH (g:Group {{id: $group_id}})
        SET {set_clause_str}
        WITH g
        MATCH (g)-[:HAS_PARAMETER]->(gp:GroupParameter)
        SET gp.value = CASE gp.name
                    {case_clause_str}
                    ELSE gp.value
        END
        """
    else:
        # No PARAMETERS to update, just update Group node
        update_query = f"""
        MATCH (g:Group {{id: $group_id}})
        SET {set_clause_str}
        """
    
    log_neo4j_query(logger, update_query, **query_params)
    session.run(update_query, **query_params)

    logger.info(f'Updated parameters for group {group_id}')


def create_empty_group(
    session,
    group_id,
    group_name,
    owner_id,
    parameters_dict,
    embedding,
    use_weights=False,
    weights=None,
):
    """
    Create an empty group in the database without any members.

    Sets all parameters from parameters_dict on the Group node and creates
    GroupParameter nodes for all PARAMETERS fields.

    Args:
        session: Neo4j session
        group_id: Group ID (string)
        group_name: Name of the group
        parameters_dict: Dict with parameter values (can include any Group property)
        embedding: Pre-computed embedding vector for the group
        use_weights: Whether to use weighted vectors (for logging purposes)
        weights: Parameter weights (for logging purposes)

    Returns:
        str: The created group_id
    """
    # Create parameter list for GroupParameter nodes (only PARAMETERS fields)
    parameters_list = [
        {'name': p, 'value': parameters_dict.get(p, 0)} for p in PARAMETERS
    ]

    # Build dynamic SET clauses for all parameters in parameters_dict
    set_clauses = [
        'g.name = $group_name',
        'g.owner_id = $owner_id',
        'g.embedding = $embedding',
    ]
    query_params = {
        'group_id': group_id,
        'group_name': group_name,
        'owner_id': owner_id,
        'embedding': embedding,
        'param_list': parameters_list,
    }

    # Add all parameters from parameters_dict (skip embedding as it's already added)
    for param_name, param_value in parameters_dict.items():
        if param_name == 'embedding':
            continue
        set_clauses.append(f'g.{param_name} = ${param_name}')
        query_params[param_name] = param_value

    set_clause_str = ',\n            '.join(set_clauses)

    # Create empty group query (no MEMBER_OF relationships)
    create_group_query = f"""
        MERGE (g:Group {{id: $group_id}})
        SET {set_clause_str}
        WITH g
        UNWIND $param_list AS param
        MERGE (gp:GroupParameter {{groupId: $group_id, name: param.name}})
        SET gp.value = param.value
        MERGE (g)-[:HAS_PARAMETER]->(gp)
        WITH DISTINCT g
        RETURN g.id as created_group_id
    """

    log_neo4j_query(
        logger,
        create_group_query,
        group_id=group_id,
        group_name=group_name,
        param_list_count=len(parameters_list),
    )

    result = session.run(
        create_group_query,
        **query_params,
    )

    record = result.single()
    if not record:
        raise RuntimeError(f'Failed to create group {group_id}')

    logger.info(f'✓ Created empty group {group_id} with name "{group_name}"')
    log_vector_operation(
        logger,
        'Created empty group vector',
        len(embedding) if embedding else 0,
        group_id,
    )

    return group_id


def change_group_owner(session, group_id, new_owner_id):
    """
    Transfer ownership of a group to a new owner.

    Args:
        session: Neo4j session
        group_id: Group ID
        new_owner_id: New owner user ID
    """
    query = """
        MATCH (g:Group {id: $group_id})
        SET g.owner_id = $new_owner_id
    """
    session.run(query, group_id=group_id, new_owner_id=new_owner_id)
    logger.info(f'✓ Changed owner of group {group_id} to {new_owner_id}')


def delete_group(session, group_id):
    """
    Delete a group by its ID, including all related GroupParameter nodes.

    Args:
        session: Neo4j session
        group_id: Group ID to delete
    """
    query = """
        MATCH (g:Group {id: $group_id})
        OPTIONAL MATCH (g)-[:HAS_PARAMETER]->(gp:GroupParameter)
        DETACH DELETE gp, g
    """
    session.run(query, group_id=group_id)
    logger.info(f'✓ Deleted group {group_id} and its parameters')


def delete_group_by_owner(session, owner_id):
    """
    Delete a group owned by a specific user, including all related GroupParameter nodes.

    Args:
        session: Neo4j session
        owner_id: Owner user ID
    """
    query = """
        MATCH (g:Group)
        WHERE g.owner_id = $owner_id
        OPTIONAL MATCH (g)-[:HAS_PARAMETER]->(gp:GroupParameter)
        DETACH DELETE gp, g
    """
    session.run(query, owner_id=owner_id)
    logger.info(f'✓ Deleted group owned by {owner_id} and its parameters')
