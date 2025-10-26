"""
User and Form operations for Neo4j database.

This module handles:
- User CRUD operations
- User parameter management
- Form data retrieval
"""

from ..config import PARAMETERS
from ..logging_utils import (
    log_database_stats,
    log_neo4j_query,
    log_vector_operation,
    setup_logger,
)
from ..user_vector_utils import (
    create_group_vector_with_weights,
    create_user_vector,
    group_parameter_weights,
)

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
    weights = weights or group_parameter_weights
    rows = []

    logger.debug(f'Processing {len(users)} users for database upsert')
    logger.debug(f'Using weights: {use_weights}, Vector caps: {caps}')

    for u in users:
        # Single-member group id and name
        group_id = f"g_{u['id']}"
        group_name = f"Group of {u.get('name') or u['id']}"

        # Prepare parameter list as separate nodes (user and group)
        param_list = [{'name': p, 'value': u.get(p)} for p in PARAMETERS]

        group_values = {p: u.get(p) for p in PARAMETERS}
        gvec = (
            create_group_vector_with_weights(group_values, PARAMETERS, weights, caps)
            if use_weights
            else create_user_vector(group_values, PARAMETERS, caps)
        )

        log_vector_operation(logger, 'Created group vector', len(gvec), group_id)

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

    count = result.single()['created']
    logger.info(f'✓ {count} groups upserted successfully (and linked to users)')

    log_database_stats(
        logger, {'groups_created': count, 'group_vectors_generated': len(rows)}
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

    Args:
        session: Neo4j session
        user_id: User ID to delete
    """
    # Delete user's parameters
    delete_params_query = """
        MATCH (u:User {id: $user_id})-[:HAS_PARAMETER]->(p:Parameter)
        DETACH DELETE p
    """
    session.run(delete_params_query, user_id=user_id)

    # Delete user's group
    delete_group_query = """
        MATCH (u:User {id: $user_id})-[:MEMBER_OF]->(g:Group)
        DETACH DELETE g
    """
    session.run(delete_group_query, user_id=user_id)

    # Delete user
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
