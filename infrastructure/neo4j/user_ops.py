"""
User and Form operations for Neo4j database.

This module handles:
- User CRUD operations
- User parameter management
- Form data retrieval
"""
from uuid import uuid4

from ..config import PARAMETERS
from ..logging_utils import (
    log_database_stats,
    log_neo4j_query,
    log_vector_operation,
    setup_logger,
)
from ..config import get_parameter_statistics, GROUP_PARAMETER_WEIGHTS
from recommendation import create_vector

# Setup logger
logger = setup_logger('roommate_db', 'INFO')


def clear_users(session):
    """Remove all User, Group nodes and their Parameter nodes and relationships."""
    # Delete Parameter nodes attached to users first to avoid orphans
    clear_params_query = 'MATCH (:User)-[:HAS_PARAMETER]->(p:Parameter) DETACH DELETE p'
    log_neo4j_query(logger, clear_params_query)
    session.run(clear_params_query)

    # Delete GroupParameter nodes
    clear_gparams_query = (
        'MATCH (:Group)-[:HAS_PARAMETER]->(p:GroupParameter) DETACH DELETE p'
    )
    log_neo4j_query(logger, clear_gparams_query)
    session.run(clear_gparams_query)

    # Now delete groups
    clear_groups_query = 'MATCH (g:Group) DETACH DELETE g'
    log_neo4j_query(logger, clear_groups_query)
    session.run(clear_groups_query)

    # Now delete users
    clear_users_query = 'MATCH (u:User) DETACH DELETE u'
    log_neo4j_query(logger, clear_users_query)
    session.run(clear_users_query)

    logger.info(
        '✓ All existing users, groups, and their parameters cleared from database'
    )
    logger.debug(
        'Database cleanup completed - all User, Group and Parameter nodes removed'
    )


def upsert_users(session, users, caps=None, use_weights=False, weights=None):
    """Insert or update users along with their single-member groups and parameters."""
    weights = weights or GROUP_PARAMETER_WEIGHTS
    
    total_users = len(users)
    logger.info(f'Starting bulk upsert of {total_users} users')
    logger.debug(f'Using weights: {use_weights}')
    
    # Process in batches to avoid overwhelming Neo4j
    BATCH_SIZE = 100  # Process 100 users at a time
    total_created = 0
    
    for batch_num, i in enumerate(range(0, total_users, BATCH_SIZE), 1):
        batch = users[i:i + BATCH_SIZE]
        batch_size = len(batch)
        
        logger.info(f'Processing batch {batch_num}/{(total_users + BATCH_SIZE - 1) // BATCH_SIZE}: users {i+1}-{i+batch_size} of {total_users}')
        
        rows = []
        for u in batch:
            # Single-member group id and name
            group_id = str(uuid4())
            group_name = f"Group of {u.get('name') or u['id']}"

            # Prepare parameter list as separate nodes (user and group)
            param_list = [{'name': p, 'value': u.get(p)} for p in PARAMETERS]

            group_values = {p: u.get(p) for p in PARAMETERS}
            gvec = create_vector(
                group_values, 
                PARAMETERS, 
                statistics=get_parameter_statistics(),
                weights=weights if use_weights else None
            )

            rows.append(
                {
                    'user': {
                        'id': u['id'],
                        'name': u.get('name'),
                        'parameters': param_list,
                    },
                    'group': {
                        'id': group_id,
                        'name': group_name,
                        'embedding': gvec,
                        'parameters': param_list,
                    },
                }
            )

        upsert_query = """
            UNWIND $rows AS row
            MERGE (u:User {id: row.user.id})
            SET u.name = row.user.name
            WITH u, row
            UNWIND row.user.parameters AS param
            MERGE (p:Parameter {userId: row.user.id, name: param.name})
            SET p.value = param.value
            MERGE (u)-[:HAS_PARAMETER]->(p)
            WITH u, row
            MERGE (g:Group {id: row.group.id})
            SET g.name = row.group.name,
                g.embedding = row.group.embedding
            MERGE (u)-[:MEMBER_OF]->(g)
            WITH g, row
            UNWIND row.group.parameters AS gparam
            MERGE (gp:GroupParameter {groupId: row.group.id, name: gparam.name})
            SET gp.value = gparam.value
            MERGE (g)-[:HAS_PARAMETER]->(gp)
            WITH DISTINCT g
            RETURN count(g) as created
        """

        log_neo4j_query(logger, upsert_query, rows_count=len(rows))
        result = session.run(upsert_query, rows=rows)

        batch_count = result.single()['created']
        total_created += batch_count
        logger.info(f'✓ Batch {batch_num} complete: {batch_count} groups created ({total_created}/{total_users} total)')

    logger.info(f'✓ All {total_created} groups upserted successfully (and linked to users)')
    log_database_stats(
        logger, {'groups_created': total_created, 'group_vectors_generated': total_users}
    )


def get_user_form(session, user_id):
    """
    Get user form data including parameters.

    Args:
        session: Neo4j session
        user_id: User ID

    Returns:
        dict: User form data with id, name, and parameters, or None if not found
    """
    user_query = """
        MATCH (u:User {id: $user_id})
        RETURN u.id as id, u.name as name
    """
    result = session.run(user_query, user_id=user_id)
    record = result.single()

    if not record:
        return None

    params = get_user_parameters(session, user_id)

    return {'id': record['id'], 'name': record['name'], **params}


def delete_user_form(session, user_id):
    """
    Delete a user and all associated data (parameters, group, relationships).
    
    Handles two scenarios:
    1. User in multi-member group: Remove user and update remaining group
    2. User in single-member group: Delete both user and group with all parameters

    Args:
        session: Neo4j session
        user_id: User ID to delete
    """
    # Import here to avoid circular dependency
    from ..config import PARAMETERS
    
    # Step 1: Check if user is in a multi-member group
    check_group_query = """
        MATCH (u:User {id: $user_id})-[:MEMBER_OF]->(g:Group)
        WITH g, COUNT {(g)<-[:MEMBER_OF]-()} as member_count
        RETURN g.id as group_id, member_count
    """
    result = session.run(check_group_query, user_id=user_id)
    record = result.single()
    
    if not record:
        logger.warning(f'User {user_id} is not in any group, deleting user only')
        # Just delete the user and their parameters
        delete_params_query = """
            MATCH (u:User {id: $user_id})-[:HAS_PARAMETER]->(p:Parameter)
            DETACH DELETE p
        """
        session.run(delete_params_query, user_id=user_id)
        
        delete_user_query = """
            MATCH (u:User {id: $user_id})
            DETACH DELETE u
        """
        session.run(delete_user_query, user_id=user_id)
        logger.info(f'✓ Deleted user {user_id} (no group found)')
        return
    
    group_id = record['group_id']
    member_count = record['member_count']
    
    if member_count > 1:
        # Multi-member group: Remove user and update group
        logger.debug(f'User {user_id} is in multi-member group {group_id} with {member_count} members')
        
        # Step 2: Delete the MEMBER_OF relationship
        delete_relationship_query = """
            MATCH (u:User {id: $user_id})-[r:MEMBER_OF]->(g:Group {id: $group_id})
            DELETE r
        """
        session.run(delete_relationship_query, user_id=user_id, group_id=group_id)
        
        # Step 3: Get remaining group members and update group
        from .group_ops import get_group_member_parameters
        remaining_members = get_group_member_parameters(session, group_id)
        
        if remaining_members:
            # Calculate new averaged parameters for the remaining group
            new_group_params = {}
            for param in PARAMETERS:
                values = [member[param] for member in remaining_members if param in member]
                if values:
                    new_group_params[param] = sum(values) / len(values)
            
            # Create new group vector
            weights = GROUP_PARAMETER_WEIGHTS
            group_values = {p: new_group_params.get(p, 0) for p in PARAMETERS}
            new_vector = create_vector(
                group_values, 
                PARAMETERS, 
                statistics=get_parameter_statistics(),
                weights=weights
            )
            
            # Update group properties and GroupParameter nodes
            update_group_query = """
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
                update_group_query,
                group_id=group_id,
                rooms=new_group_params.get('rooms', 0),
                roommates=new_group_params.get('roommates', 0),
                budget=new_group_params.get('budget', 0),
                months=new_group_params.get('months', 0),
                embedding=new_vector,
            )
            logger.info(f'✓ Updated group {group_id} after removing user {user_id}')
    else:
        # Single-member group: Delete group with all GroupParameter nodes
        logger.debug(f'User {user_id} is in single-member group {group_id}')
        delete_group_query = """
            MATCH (u:User {id: $user_id})-[:MEMBER_OF]->(g:Group)
            OPTIONAL MATCH (g)-[:HAS_PARAMETER]->(gp:GroupParameter)
            DETACH DELETE gp, g
        """
        session.run(delete_group_query, user_id=user_id)
        logger.info(f'✓ Deleted group {group_id} and its parameters')
    
    # Step 4: Delete user's parameters
    delete_params_query = """
        MATCH (u:User {id: $user_id})-[:HAS_PARAMETER]->(p:Parameter)
        DETACH DELETE p
    """
    session.run(delete_params_query, user_id=user_id)
    
    # Step 5: Delete user
    delete_user_query = """
        MATCH (u:User {id: $user_id})
        DETACH DELETE u
    """
    session.run(delete_user_query, user_id=user_id)
    logger.info(f'✓ Deleted user {user_id} and all associated data')


def get_user_parameters(session, user_id):
    """Fetch user parameter values from Parameter nodes with safe defaults."""
    query = """
        MATCH (u:User {id: $user_id})
        WITH u
        OPTIONAL MATCH (u)-[:HAS_PARAMETER]->(pr:Parameter {name: 'rooms'})
        OPTIONAL MATCH (u)-[:HAS_PARAMETER]->(pm:Parameter {name: 'roommates'})
        OPTIONAL MATCH (u)-[:HAS_PARAMETER]->(pb:Parameter {name: 'budget'})
        OPTIONAL MATCH (u)-[:HAS_PARAMETER]->(pn:Parameter {name: 'months'})
        RETURN coalesce(pr.value, 0) as rooms,
               coalesce(pm.value, 0) as roommates,
               coalesce(pb.value, 0) as budget,
               coalesce(pn.value, 1) as months
    """
    record = session.run(query, user_id=user_id).single()
    if not record:
        return {'rooms': 0, 'roommates': 0, 'budget': 0, 'months': 1}
    return {p: record[p] for p in PARAMETERS}
