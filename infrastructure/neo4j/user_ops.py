"""
User and Form operations for Neo4j database.

This module handles:
- User CRUD operations
- User parameter management
- Form data retrieval
"""

from uuid import uuid4

from recommendation import create_vector

from ..config import GROUP_PARAMETER_WEIGHTS, PARAMETERS, get_parameter_statistics
from ..logging_utils import (
    log_database_stats,
    log_neo4j_query,
    setup_logger,
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


def upsert_users(session, users):
    """Insert or update users and their parameters."""
    
    logger.info(f'Starting upsert of {len(users)} users')
    
    rows = []
    for user in users:
        param_list = [{'name': p, 'value': user.get(p)} for p in PARAMETERS]
        rows.append({
            'id': user['id'],
            'name': user.get('name', ''),
            'surname': user.get('surname', ''),
            'geo_lat': user.get('geo_lat', 0.0),
            'geo_lon': user.get('geo_lon', 0.0),
            'photos': user.get('photos', []),
            'age': user.get('age', 0),
            'smoking': user.get('smoking', False),
            'alko': user.get('alko', False),
            'pet': user.get('pet', False),
            'sex': user.get('sex', 1),  # Default to MALE
            'user_type': user.get('user_type', 1),  # Default to STUDENT
            'description': user.get('description', ''),
            'parameters': param_list,
        })
    
    # Single query for ALL users with metadata fields
    upsert_query = """
        UNWIND $rows AS row
        MERGE (u:User {id: row.id})
        SET u.name = row.name,
            u.surname = row.surname,
            u.geo_lat = row.geo_lat,
            u.geo_lon = row.geo_lon,
            u.photos = row.photos,
            u.age = row.age,
            u.smoking = row.smoking,
            u.alko = row.alko,
            u.pet = row.pet,
            u.sex = row.sex,
            u.user_type = row.user_type,
            u.description = row.description
        WITH u, row
        UNWIND row.parameters AS param
        MERGE (p:Parameter {userId: row.id, name: param.name})
        SET p.value = param.value
        MERGE (u)-[:HAS_PARAMETER]->(p)
        RETURN count(DISTINCT u) as created
    """
    
    log_neo4j_query(logger, upsert_query, rows_count=len(rows))
    result = session.run(upsert_query, rows=rows)
    
    user_count = result.single()['created']
    logger.info(f'✓ Upserted {user_count} users successfully')



def get_user_form(session, user_id):
    """
    Get user form data including parameters.

    Args:
        session: Neo4j session
        user_id: User ID

    Returns:
        dict: User form data with id, name, metadata fields, and parameters, or None if not found
    """
    user_query = """
        MATCH (u:User {id: $user_id})
        RETURN u.id as id,
               u.name as name,
               u.surname as surname,
               u.geo_lat as geo_lat,
               u.geo_lon as geo_lon,
               u.photos as photos,
               u.age as age,
               u.smoking as smoking,
               u.alko as alko,
               u.pet as pet,
               u.sex as sex,
               u.user_type as user_type,
               u.description as description
    """
    result = session.run(user_query, user_id=user_id)
    record = result.single()

    if not record:
        return None

    # Convert record to dict with all metadata fields
    user_data = {
        'id': record['id'],
        'name': record['name'],
        'surname': record.get('surname', ''),
        'geo_lat': record.get('geo_lat', 0.0),
        'geo_lon': record.get('geo_lon', 0.0),
        'photos': record.get('photos', []),
        'age': record.get('age', 0),
        'smoking': record.get('smoking', False),
        'alko': record.get('alko', False),
        'pet': record.get('pet', False),
        'sex': record.get('sex', 1),
        'user_type': record.get('user_type', 1),
        'description': record.get('description', ''),
    }
    
    # Get parameter node values (rooms, roommates, budget, months)
    params = get_user_parameters(session, user_id)

    return {**user_data, **params}


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
        logger.debug(
            f'User {user_id} is in multi-member group {group_id} with {member_count} members'
        )

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
                values = [
                    member[param] for member in remaining_members if param in member
                ]
                if values:
                    new_group_params[param] = sum(values) / len(values)

            # Create new group vector
            weights = GROUP_PARAMETER_WEIGHTS
            group_values = {p: new_group_params.get(p, 0) for p in PARAMETERS}
            new_vector = create_vector(
                group_values,
                PARAMETERS,
                statistics=get_parameter_statistics(),
                weights=weights,
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
