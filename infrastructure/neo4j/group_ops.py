"""
Group operations for Neo4j database.

This module handles:
- Group CRUD operations
- Group membership management
- Group parameter calculations
- Member addition and removal
"""

from uuid import uuid4

from recommendation import create_vector

from ..config import GROUP_PARAMETER_WEIGHTS, PARAMETERS, get_parameter_statistics
from ..logging_utils import (
    log_neo4j_query,
    log_vector_operation,
    setup_logger,
)

# Setup logger
logger = setup_logger('roommate_db', 'INFO')


def add_user_to_group(
    session, user_id, target_group_id, caps=None, use_weights=False, weights=None
):
    """
    Add a user to an existing group, delete their old group, and update group parameters.

    Args:
        session: Neo4j session
        user_id: ID of user to add
        target_group_id: ID of group to join
        caps: Normalization caps for vector creation
        use_weights: Whether to use weighted vectors
        weights: Parameter weights for group vector creation

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Get user's current group
        current_group_query = """
            MATCH (u:User {id: $user_id})-[:MEMBER_OF]->(g:Group)
            RETURN g.id as current_group_id
        """
        result = session.run(current_group_query, user_id=user_id)
        record = result.single()
        current_group_id = record['current_group_id'] if record else None

        if not current_group_id:
            logger.warning(f'User {user_id} is not a member of any group')
            return False

        # Only proceed if user is not already in the target group
        if current_group_id == target_group_id:
            logger.info(
                f'User {user_id} is already a member of group {target_group_id}'
            )
            return True

        # Import here to avoid circular dependency
        from .user_ops import get_user_parameters

        # Get all users in the target group to calculate new parameters (from Parameter nodes)
        target_members = get_group_member_parameters(session, target_group_id)

        # Add the new user to the list
        new_user_record = get_user_parameters(session, user_id)
        if new_user_record:
            target_members.append({'user_id': user_id, **new_user_record})

        # Calculate new group parameters (average of all members)
        if target_members:
            new_group_params = {}
            for param in PARAMETERS:
                values = [member[param] for member in target_members if param in member]
                if values:
                    new_group_params[param] = sum(values) / len(values)

            # Update group parameters and vector
            group_values = {p: new_group_params.get(p, 0) for p in PARAMETERS}
            weights = weights or GROUP_PARAMETER_WEIGHTS

            new_vector = create_vector(
                group_values,
                PARAMETERS,
                statistics=get_parameter_statistics(),
                weights=weights if use_weights else None,
            )

            # Update the group in database
            update_group_query = """
                MATCH (g:Group {id: $target_group_id})
                SET g.rooms = $rooms, g.roommates = $roommates,
                    g.budget = $budget, g.months = $months,
                    g.embedding = $embedding
                WITH g
                MATCH (g)-[:HAS_PARAMETER]->(gp:GroupParameter)
                SET gp.value = CASE gp.name
                    WHEN 'rooms' THEN $rooms
                    WHEN 'roommates' THEN $roommates
                    WHEN 'budget' THEN $budget
                    WHEN 'months' THEN $months
                    ELSE gp.value
                END
            """
            session.run(
                update_group_query,
                target_group_id=target_group_id,
                rooms=new_group_params.get('rooms', 0),
                roommates=new_group_params.get('roommates', 0),
                budget=new_group_params.get('budget', 0),
                months=new_group_params.get('months', 0),
                embedding=new_vector,
            )

            # Move user to new group and delete old group with all its parameters
            # CRITICAL: Must explicitly DELETE old MEMBER_OF relationship first
            move_user_query = """
                MATCH (u:User {id: $user_id})
                MATCH (old_g:Group {id: $current_group_id})
                MATCH (u)-[old_rel:MEMBER_OF]->(old_g)
                DELETE old_rel
                WITH u, old_g
                MATCH (g:Group {id: $target_group_id})
                MERGE (u)-[:MEMBER_OF]->(g)
                WITH old_g
                OPTIONAL MATCH (old_g)-[:HAS_PARAMETER]->(gp:GroupParameter)
                DETACH DELETE gp, old_g
            """
            session.run(
                move_user_query,
                user_id=user_id,
                target_group_id=target_group_id,
                current_group_id=current_group_id,
            )

            logger.info(
                f'✓ User {user_id} moved from group {current_group_id} to group {target_group_id}'
            )
            log_vector_operation(
                logger, 'Updated group vector', len(new_vector), target_group_id
            )
            return True
        else:
            logger.warning(f'No members found in target group {target_group_id}')
            return False

    except Exception as e:
        logger.error(f'Error adding user {user_id} to group {target_group_id}: {e}')
        return False


def remove_user_from_group(
    session, user_id, caps: dict | None = None, use_weights=False, weights=None
):
    """
    Remove a user from their current group and create a new single-member group for them.

    This function implements Neo4j best practices:
    - Explicit relationship deletion with DELETE
    - In-place property updates with SET
    - Proper error handling for edge cases
    - Atomic operations where possible

    Args:
        session: Neo4j session
        user_id: ID of user to remove
        caps: Normalization caps for vector creation
        use_weights: Whether to use weighted vectors
        weights: Parameter weights for group vector creation

    Returns:
        str: ID of the new single-member group

    Raises:
        ValueError: If user is not in a group or is already in a single-member group
    """
    try:
        weights = weights or GROUP_PARAMETER_WEIGHTS

        # Import here to avoid circular dependency
        from .user_ops import get_user_parameters

        # Step 1: Validate user exists and get current group info
        validation_query = """
            MATCH (u:User {id: $user_id})-[:MEMBER_OF]->(g:Group)
            WITH g, COUNT {(g)<-[:MEMBER_OF]-()} as member_count
            RETURN g.id as current_group_id, member_count
        """
        log_neo4j_query(logger, validation_query, user_id=user_id)
        result = session.run(validation_query, user_id=user_id)
        record = result.single()

        if not record:
            logger.warning(f'User {user_id} is not a member of any group')
            raise ValueError(f'User {user_id} is not a member of any group')

        current_group_id = record['current_group_id']
        member_count = record['member_count']

        # Check if user is already in a single-member group
        if member_count == 1:
            logger.warning(
                f'User {user_id} is already in a single-member group {current_group_id}'
            )
            raise ValueError(f'User {user_id} is already in a single-member group')

        logger.debug(
            f'User {user_id} is in group {current_group_id} with {member_count} members'
        )

        # Step 2: Get user parameters for new group creation
        user_params = get_user_parameters(session, user_id)

        # Step 3: Explicitly delete the MEMBER_OF relationship
        delete_relationship_query = """
            MATCH (u:User {id: $user_id})-[r:MEMBER_OF]->(g:Group {id: $current_group_id})
            DELETE r
            RETURN g.id as old_group_id
        """
        log_neo4j_query(
            logger,
            delete_relationship_query,
            user_id=user_id,
            current_group_id=current_group_id,
        )
        session.run(
            delete_relationship_query,
            user_id=user_id,
            current_group_id=current_group_id,
        )
        logger.debug(
            f'Deleted MEMBER_OF relationship from user {user_id} to group {current_group_id}'
        )

        # Step 4: Update old group with remaining members or delete if empty
        remaining_members = get_group_member_parameters(session, current_group_id)

        if remaining_members:
            # Calculate new averaged parameters for the remaining group
            new_group_params = {}
            for param in PARAMETERS:
                values = [
                    member[param] for member in remaining_members if param in member
                ]
                if values:
                    new_group_params[param] = sum(values) / len(values)

            # Create new group vector
            group_values = {p: new_group_params.get(p, 0) for p in PARAMETERS}
            if use_weights:
                new_vector = create_vector(
                    group_values,
                    PARAMETERS,
                    statistics=get_parameter_statistics(),
                    weights=weights if use_weights else None,
                )

            # Update group properties and GroupParameter nodes in place
            update_group_query = """
                MATCH (g:Group {id: $current_group_id})
                SET g.rooms = $rooms,
                    g.roommates = $roommates,
                    g.budget = $budget,
                    g.months = $months,
                    g.embedding = $embedding
                WITH g
                MATCH (g)-[:HAS_PARAMETER]->(gp:GroupParameter)
                SET gp.value = CASE gp.name
                    WHEN 'rooms' THEN $rooms
                    WHEN 'roommates' THEN $roommates
                    WHEN 'budget' THEN $budget
                    WHEN 'months' THEN $months
                    ELSE gp.value
                END
                RETURN g.id as updated_group_id
            """
            log_neo4j_query(
                logger,
                update_group_query,
                current_group_id=current_group_id,
                rooms=new_group_params.get('rooms', 0),
                roommates=new_group_params.get('roommates', 0),
                budget=new_group_params.get('budget', 0),
                months=new_group_params.get('months', 0),
            )
            session.run(
                update_group_query,
                current_group_id=current_group_id,
                rooms=new_group_params.get('rooms', 0),
                roommates=new_group_params.get('roommates', 0),
                budget=new_group_params.get('budget', 0),
                months=new_group_params.get('months', 0),
                embedding=new_vector,
            )

            log_vector_operation(
                logger,
                'Updated remaining group vector',
                len(new_vector),
                current_group_id,
            )
            logger.info(
                f'✓ Updated group {current_group_id} with {len(remaining_members)} remaining members'
            )
        else:
            # No remaining members, delete the empty group with all its parameters
            delete_empty_group_query = """
                MATCH (g:Group {id: $current_group_id})
                OPTIONAL MATCH (g)-[:HAS_PARAMETER]->(gp:GroupParameter)
                DETACH DELETE gp, g
            """
            log_neo4j_query(
                logger,
                delete_empty_group_query,
                current_group_id=current_group_id,
            )
            session.run(
                delete_empty_group_query,
                current_group_id=current_group_id,
            )
            logger.info(f'✓ Deleted empty group {current_group_id}')

        # Step 5: Create new single-member group for the user
        new_group_id = str(uuid4())
        new_group_name = f'Group of {user_id}'

        # Create vector for new single-member group
        if use_weights:
            new_user_vector = create_vector(
                user_params,
                PARAMETERS,
                statistics=get_parameter_statistics(),
                weights=weights if use_weights else None,
            )

        # Create new group and establish relationship in a single atomic query
        create_new_group_query = """
            MATCH (u:User {id: $user_id})
            MERGE (g:Group {id: $new_group_id})
            SET g.name = $group_name,
                g.rooms = $rooms,
                g.roommates = $roommates,
                g.budget = $budget,
                g.months = $months,
                g.embedding = $embedding
            MERGE (u)-[:MEMBER_OF]->(g)
            WITH g
            UNWIND $param_list AS param
            MERGE (gp:GroupParameter {groupId: $new_group_id, name: param.name})
            SET gp.value = param.value
            MERGE (g)-[:HAS_PARAMETER]->(gp)
            RETURN g.id as new_group_id
        """

        parameters_list = [
            {'name': p, 'value': user_params.get(p, 0)} for p in PARAMETERS
        ]
        log_neo4j_query(
            logger,
            create_new_group_query,
            user_id=user_id,
            new_group_id=new_group_id,
            param_list_count=len(parameters_list),
        )

        session.run(
            create_new_group_query,
            user_id=user_id,
            new_group_id=new_group_id,
            group_name=new_group_name,
            rooms=user_params.get('rooms', 0),
            roommates=user_params.get('roommates', 0),
            budget=user_params.get('budget', 0),
            months=user_params.get('months', 0),
            embedding=new_user_vector,
            param_list=parameters_list,
        )

        logger.info(
            f'✓ User {user_id} removed from group {current_group_id}, created new group {new_group_id}'
        )
        log_vector_operation(
            logger,
            'Created new single-member group vector',
            len(new_user_vector),
            new_group_id,
        )

        return new_group_id

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

    return {
        'id': group['id'],
        'name': group['name'],
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
        RETURN u.id as id,
               u.name as name,
               coalesce(pr.value, 0) as rooms,
               coalesce(pm.value, 0) as roommates,
               coalesce(pb.value, 0) as budget,
               coalesce(pn.value, 1) as months
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

    Args:
        session: Neo4j session
        group_id: Group ID
        parameters_dict: Dict with parameter values (rooms, roommates, budget, months)
        caps: Normalization caps
        use_weights: Whether to use weighted vectors
        weights: Parameter weights
    """
    # Create new group vector
    group_values = {p: parameters_dict.get(p, 0) for p in PARAMETERS}
    new_vector = create_vector(
        group_values,
        PARAMETERS,
        statistics=get_parameter_statistics(),
        weights=weights if use_weights else None,
    )

    # Update group properties and GroupParameter nodes
    update_query = """
        MATCH (g:Group {id: $group_id})
        SET g.rooms = $rooms,
            g.roommates = $roommates,
            g.budget = $budget,
            g.months = $months,
            g.embedding = $embedding
        WITH g
        MATCH (g)-[:HAS_PARAMETER]->(gp:GroupParameter)
        SET gp.value = CASE gp.name
            WHEN 'rooms' THEN $rooms
            WHEN 'roommates' THEN $roommates
            WHEN 'budget' THEN $budget
            WHEN 'months' THEN $months
            ELSE gp.value
        END
    """
    session.run(
        update_query,
        group_id=group_id,
        rooms=parameters_dict.get('rooms', 0),
        roommates=parameters_dict.get('roommates', 0),
        budget=parameters_dict.get('budget', 0),
        months=parameters_dict.get('months', 0),
        embedding=new_vector,
    )

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

    Args:
        session: Neo4j session
        group_id: Group ID (string)
        group_name: Name of the group
        parameters_dict: Dict with parameter values (rooms, roommates, budget, months)
        embedding: Pre-computed embedding vector for the group
        use_weights: Whether to use weighted vectors (for logging purposes)
        weights: Parameter weights (for logging purposes)

    Returns:
        str: The created group_id
    """
    # Create parameter list for GroupParameter nodes
    parameters_list = [
        {'name': p, 'value': parameters_dict.get(p, 0)} for p in PARAMETERS
    ]

    # Create empty group query (no MEMBER_OF relationships)
    create_group_query = """
        MERGE (g:Group {id: $group_id})
        SET g.name = $group_name,
            g.rooms = $rooms,
            g.owner_id = $owner_id,
            g.roommates = $roommates,
            g.budget = $budget,
            g.months = $months,
            g.embedding = $embedding
        WITH g
        UNWIND $param_list AS param
        MERGE (gp:GroupParameter {groupId: $group_id, name: param.name})
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
        owner_id=owner_id,
        group_id=group_id,
        group_name=group_name,
        rooms=parameters_dict.get('rooms', 0),
        roommates=parameters_dict.get('roommates', 0),
        budget=parameters_dict.get('budget', 0),
        months=parameters_dict.get('months', 0),
        embedding=embedding,
        param_list=parameters_list,
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
