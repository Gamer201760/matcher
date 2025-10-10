# neo4j_neighbors_example.py
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, Neo4jError
import os
from user_vector_utils import (
    create_user_vector,
    create_group_vector_with_weights,
    group_parameter_weights,
    euclidean_distance,
)
from logging_utils import (
    setup_logger,
    log_neo4j_query,
    log_vector_operation,
    log_similarity_results,
    log_database_stats
)
import dotenv
dotenv.load_dotenv()

# Setup logger
logger = setup_logger("roommate_db", "INFO")

PARAMETERS = ['rooms', 'roommates', 'budget', 'months']

def get_driver(uri=None, user=None, password=None):
    uri = uri or os.getenv('NEO4J_URI')  # prefer IPv4 localhost
    user = user or os.getenv('NEO4J_USERNAME')
    password = password or os.getenv('NEO4J_PASSWORD')
    return GraphDatabase.driver(uri, auth=(user, password))

def ensure_constraints_and_index(session, dims):
    """Ensure required constraints and vector indexes exist for User and Group nodes."""
    logger.debug(f"Setting up database constraints and indexes for {dims}-dimensional vectors")
    
    try:
        # Ensure a unique id constraint for Users (proper Neo4j syntax)
        constraint_query = """
            CREATE CONSTRAINT user_id_unique IF NOT EXISTS
            FOR (u:User) REQUIRE u.id IS UNIQUE
        """
        log_neo4j_query(logger, constraint_query)
        session.run(constraint_query)
        logger.info("✓ User ID uniqueness constraint ensured")
        
        # Ensure a unique constraint for Parameter nodes per (userId, name)
        param_constraint_query = """
            CREATE CONSTRAINT parameter_unique IF NOT EXISTS
            FOR (p:Parameter) REQUIRE (p.userId, p.name) IS UNIQUE
        """
        log_neo4j_query(logger, param_constraint_query)
        session.run(param_constraint_query)
        logger.info("✓ Parameter uniqueness constraint ensured (userId, name)")

        # Ensure a unique id constraint for Groups
        group_constraint_query = """
            CREATE CONSTRAINT group_id_unique IF NOT EXISTS
            FOR (g:Group) REQUIRE g.id IS UNIQUE
        """
        log_neo4j_query(logger, group_constraint_query)
        session.run(group_constraint_query)
        logger.info("✓ Group ID uniqueness constraint ensured")

        # Ensure a unique constraint for GroupParameter (groupId, name)
        gparam_constraint_query = """
            CREATE CONSTRAINT group_parameter_unique IF NOT EXISTS
            FOR (p:GroupParameter) REQUIRE (p.groupId, p.name) IS UNIQUE
        """
        log_neo4j_query(logger, gparam_constraint_query)
        session.run(gparam_constraint_query)
        logger.info("✓ GroupParameter uniqueness constraint ensured (groupId, name)")
        
        # Check if vector index exists
        index_check_query = """
            SHOW INDEXES
            YIELD name, type, entityType, labelsOrTypes, properties
            WHERE type = 'VECTOR' AND entityType = 'NODE'
              AND 'User' IN labelsOrTypes AND 'embedding' IN properties
            RETURN name LIMIT 1
        """
        log_neo4j_query(logger, index_check_query)
        result = session.run(index_check_query)
        
        if result.peek() is None:
            # Create vector index for User.embedding using new syntax
            index_create_query = """
                CREATE VECTOR INDEX user_vec_index IF NOT EXISTS
                FOR (u:User) ON (u.embedding)
                OPTIONS {indexConfig: {
                    `vector.dimensions`: $dims,
                    `vector.similarity_function`: 'euclidean'
                }}
            """
            log_neo4j_query(logger, index_create_query, {"dims": dims})
            session.run(index_create_query, dims=dims)
            logger.info(f"✓ Vector index 'user_vec_index' created with {dims} dimensions")
        else:
            logger.info("✓ Vector index already exists")
            logger.debug("Skipping vector index creation - index already present")

        # Check if GROUP vector index exists
        gindex_check_query = """
            SHOW INDEXES
            YIELD name, type, entityType, labelsOrTypes, properties
            WHERE type = 'VECTOR' AND entityType = 'NODE'
              AND 'Group' IN labelsOrTypes AND 'embedding' IN properties
            RETURN name LIMIT 1
        """
        log_neo4j_query(logger, gindex_check_query)
        gresult = session.run(gindex_check_query)

        if gresult.peek() is None:
            gindex_create_query = """
                CREATE VECTOR INDEX group_vec_index IF NOT EXISTS
                FOR (g:Group) ON (g.embedding)
                OPTIONS {indexConfig: {
                    `vector.dimensions`: $dims,
                    `vector.similarity_function`: 'euclidean'
                }}
            """
            log_neo4j_query(logger, gindex_create_query, {"dims": dims})
            session.run(gindex_create_query, dims=dims)
            logger.info(f"✓ Vector index 'group_vec_index' created with {dims} dimensions")
        else:
            logger.info("✓ Group vector index already exists")
            logger.debug("Skipping group vector index creation - index already present")
            
    except Neo4jError as e:
        logger.warning(f"Could not ensure constraints/indexes: {e}")
        logger.debug("Continuing execution - constraints might already exist")
        # Continue execution - constraints might already exist

def clear_users(session):
    """Remove all User, Group nodes and their Parameter nodes and relationships."""
    # Delete Parameter nodes attached to users first to avoid orphans
    clear_params_query = "MATCH (:User)-[:HAS_PARAMETER]->(p:Parameter) DETACH DELETE p"
    log_neo4j_query(logger, clear_params_query)
    session.run(clear_params_query)

    # Delete GroupParameter nodes
    clear_gparams_query = "MATCH (:Group)-[:HAS_PARAMETER]->(p:GroupParameter) DETACH DELETE p"
    log_neo4j_query(logger, clear_gparams_query)
    session.run(clear_gparams_query)

    # Now delete groups
    clear_groups_query = "MATCH (g:Group) DETACH DELETE g"
    log_neo4j_query(logger, clear_groups_query)
    session.run(clear_groups_query)

    # Now delete users
    clear_users_query = "MATCH (u:User) DETACH DELETE u"
    log_neo4j_query(logger, clear_users_query)
    session.run(clear_users_query)

    logger.info("✓ All existing users, groups, and their parameters cleared from database")
    logger.debug("Database cleanup completed - all User, Group and Parameter nodes removed")

def upsert_users(session, users, caps=None, use_weights=False, weights=None):
    """Insert or update users along with their single-member groups and parameters."""
    weights = weights or group_parameter_weights
    rows = []
    
    logger.debug(f"Processing {len(users)} users for database upsert")
    logger.debug(f"Using weights: {use_weights}, Vector caps: {caps}")
    
    for u in users:
        # Single-member group id and name
        group_id = f"g_{u['id']}"
        group_name = f"Group of {u.get('name') or u['id']}"

        # Prepare parameter list as separate nodes (user and group)
        param_list = [{
            'name': p,
            'value': u.get(p)
        } for p in PARAMETERS]

        group_values = {p: u.get(p) for p in PARAMETERS}
        gvec = create_group_vector_with_weights(group_values, PARAMETERS, weights, caps) if use_weights \
              else create_user_vector(group_values, PARAMETERS, caps)

        log_vector_operation(logger, "Created group vector", len(gvec), group_id)

        rows.append({
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
            }
        })
    
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
    
    log_neo4j_query(logger, upsert_query, {"rows_count": len(rows)})
    result = session.run(upsert_query, rows=rows)
    
    count = result.single()['created']
    logger.info(f"✓ {count} groups upserted successfully (and linked to users)")
    
    log_database_stats(logger, {"groups_created": count, "group_vectors_generated": len(rows)})

def find_similar(session, vector, top_k=5, exclude_id=None):
    """Find similar groups using vector similarity search."""
    log_vector_operation(logger, "Executing similarity search", len(vector), exclude_id)
    
    similarity_query = """
        CALL db.index.vector.queryNodes($indexName, $k, $vector)
        YIELD node, score
        WHERE $excludeId IS NULL OR node.id <> $excludeId
        RETURN node.id AS id, node.name AS name, score
        ORDER BY score DESC
        LIMIT $k
    """
    
    params = {
        'indexName': 'group_vec_index', 
        'k': top_k, 
        'vector': vector, 
        'excludeId': exclude_id
    }
    log_neo4j_query(logger, similarity_query, {**params, 'vector': f'[{len(vector)} elements]'})
    
    records = session.run(similarity_query, **params)
    results = [r.data() for r in records]
    
    if exclude_id:
        log_similarity_results(logger, exclude_id, results, top_k)
    
    return results

def find_similar_local(users, query_user, caps=None, use_weights=False, weights=None, top_k=5):
    """Find similar groups using local computation (fallback method)."""
    weights = weights or group_parameter_weights
    query_user_id = query_user.get('id')
    query_group_id = f"g_{query_user_id}"
    
    logger.debug(f"Computing local similarity for group {query_group_id} against {len(users)} groups")
    logger.debug(f"Using weights: {use_weights}, caps: {caps}")
    
    group_values = {p: query_user.get(p) for p in PARAMETERS}
    if use_weights:
        qvec = create_group_vector_with_weights(group_values, PARAMETERS, weights, caps)
    else:
        qvec = create_user_vector(group_values, PARAMETERS, caps)
    
    log_vector_operation(logger, "Generated group query vector", len(qvec), query_group_id)
    
    results = []
    for u in users:
        uid = u['id']
        gid = f"g_{uid}"
        if gid == query_group_id:
            continue
            
        values = {p: u.get(p) for p in PARAMETERS}
        if use_weights:
            uvec = create_group_vector_with_weights(values, PARAMETERS, weights, caps)
        else:
            uvec = create_user_vector(values, PARAMETERS, caps)
        
        # euclidean_distance returns distance; convert to similarity
        distance = euclidean_distance(qvec, uvec)
        sim = 1.0 - distance
        
        logger.debug(f"Similarity between {query_group_id} and {gid}: {sim:.4f} (distance: {distance:.4f})")
        results.append({'id': gid, 'name': f"Group of {u.get('name') or uid}", 'score': sim})
    
    results.sort(key=lambda r: r['score'], reverse=True)
    final_results = results[:top_k]
    
    log_similarity_results(logger, query_group_id, final_results, top_k)
    return final_results

def clean_db():
    """Clean the entire database after user confirmation."""
    logger.warning("Database cleaning requested - this will delete ALL data")
    confirmation = input("⚠️  This will delete ALL data in the database. Are you sure? (type 'YES' to confirm): ")
    
    if confirmation != 'YES':
        logger.info("Database cleaning cancelled by user")
        return False
        
    logger.info("Starting complete database cleanup...")
    
    try:
        with get_driver() as driver:
            with driver.session() as session:
                # Delete all nodes and relationships
                delete_query = "MATCH (n) DETACH DELETE n"
                log_neo4j_query(logger, delete_query)
                session.run(delete_query)
                logger.info("✓ All nodes and relationships deleted")
                
                # Drop all indexes (except built-in ones)
                indexes_query = """
                    SHOW INDEXES
                    YIELD name, type
                    WHERE type = 'VECTOR'
                    RETURN name
                """
                log_neo4j_query(logger, indexes_query)
                indexes_result = session.run(indexes_query)
                
                dropped_indexes = 0
                for record in indexes_result:
                    index_name = record['name']
                    try:
                        drop_index_query = f"DROP INDEX {index_name}"
                        log_neo4j_query(logger, drop_index_query)
                        session.run(drop_index_query)
                        logger.info(f"✓ Dropped index: {index_name}")
                        dropped_indexes += 1
                    except Neo4jError as e:
                        logger.debug(f"Could not drop index {index_name}: {e}")
                
                # Drop all constraints
                constraints_query = """
                    SHOW CONSTRAINTS
                    YIELD name
                    RETURN name
                """
                log_neo4j_query(logger, constraints_query)
                constraints_result = session.run(constraints_query)
                
                dropped_constraints = 0
                for record in constraints_result:
                    constraint_name = record['name']
                    try:
                        drop_constraint_query = f"DROP CONSTRAINT {constraint_name}"
                        log_neo4j_query(logger, drop_constraint_query)
                        session.run(drop_constraint_query)
                        logger.info(f"✓ Dropped constraint: {constraint_name}")
                        dropped_constraints += 1
                    except Neo4jError as e:
                        logger.debug(f"Could not drop constraint {constraint_name}: {e}")
                        
                logger.info("✅ Database cleaned successfully!")
                log_database_stats(logger, {
                    "indexes_dropped": dropped_indexes,
                    "constraints_dropped": dropped_constraints
                })
                return True
                
    except Exception as e:
        logger.error(f"Error cleaning database: {e}")
        return False


def add_user_to_group(session, user_id, target_group_id, caps=None, use_weights=False, weights=None):
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
            logger.warning(f"User {user_id} is not a member of any group")
            return False

        # Only proceed if user is not already in the target group
        if current_group_id == target_group_id:
            logger.info(f"User {user_id} is already a member of group {target_group_id}")
            return True

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
            weights = weights or group_parameter_weights

            if use_weights:
                new_vector = create_group_vector_with_weights(group_values, PARAMETERS, weights, caps)
            else:
                new_vector = create_user_vector(group_values, PARAMETERS, caps)

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
            session.run(update_group_query,
                       target_group_id=target_group_id,
                       rooms=new_group_params.get('rooms', 0),
                       roommates=new_group_params.get('roommates', 0),
                       budget=new_group_params.get('budget', 0),
                       months=new_group_params.get('months', 0),
                       embedding=new_vector)

            # Move user to new group and delete old group
            move_user_query = """
                MATCH (u:User {id: $user_id})
                MATCH (g:Group {id: $target_group_id})
                MATCH (old_g:Group {id: $current_group_id})
                SET u.group_id = $target_group_id
                MERGE (u)-[:MEMBER_OF]->(g)
                WITH old_g
                DETACH DELETE old_g
            """
            session.run(move_user_query,
                       user_id=user_id,
                       target_group_id=target_group_id,
                       current_group_id=current_group_id)

            logger.info(f"✓ User {user_id} moved from group {current_group_id} to group {target_group_id}")
            log_vector_operation(logger, "Updated group vector", len(new_vector), target_group_id)
            return True
        else:
            logger.warning(f"No members found in target group {target_group_id}")
            return False

    except Exception as e:
        logger.error(f"Error adding user {user_id} to group {target_group_id}: {e}")
        return False


def remove_user_from_group(session, user_id, caps=None, use_weights=False, weights=None):
    """
    Remove a user from their current group and create a new single-member group for them.

    Args:
        session: Neo4j session
        user_id: ID of user to remove
        caps: Normalization caps for vector creation
        use_weights: Whether to use weighted vectors
        weights: Parameter weights for group vector creation

    Returns:
        str: ID of the new single-member group, or None if failed
    """
    try:
        # Get user's current group and parameters
        user_group_query = """
            MATCH (u:User {id: $user_id})-[:MEMBER_OF]->(g:Group)
            RETURN g.id as current_group_id
        """
        result = session.run(user_group_query, user_id=user_id)
        record = result.single()

        if not record:
            logger.warning(f"User {user_id} is not a member of any group")
            return None

        current_group_id = record['current_group_id']
        user_params = get_user_parameters(session, user_id)

        # Get remaining members of the current group
        remaining_members = get_group_member_parameters(session, current_group_id, exclude_user_id=user_id)

        # Update old group if there are remaining members
        if remaining_members:
            new_group_params = {}
            for param in PARAMETERS:
                values = [member[param] for member in remaining_members if param in member]
                if values:
                    new_group_params[param] = sum(values) / len(values)

            group_values = {p: new_group_params.get(p, 0) for p in PARAMETERS}
            weights = weights or group_parameter_weights

            if use_weights:
                new_vector = create_group_vector_with_weights(group_values, PARAMETERS, weights, caps)
            else:
                new_vector = create_user_vector(group_values, PARAMETERS, caps)

            update_group_query = """
                MATCH (g:Group {id: $current_group_id})
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
            session.run(update_group_query,
                       current_group_id=current_group_id,
                       rooms=new_group_params.get('rooms', 0),
                       roommates=new_group_params.get('roommates', 0),
                       budget=new_group_params.get('budget', 0),
                       months=new_group_params.get('months', 0),
                       embedding=new_vector)
        else:
            # Delete empty group
            session.run("MATCH (g:Group {id: $current_group_id}) DETACH DELETE g",
                       current_group_id=current_group_id)

        # Create new single-member group for the removed user
        new_group_id = f"g_{user_id}"
        new_group_name = f"Group of {user_id}"

        weights = weights or group_parameter_weights
        if use_weights:
            new_vector = create_group_vector_with_weights(user_params, PARAMETERS, weights, caps)
        else:
            new_vector = create_user_vector(user_params, PARAMETERS, caps)

        # Update user relationship and create new group
        create_new_group_query = """
            MATCH (u:User {id: $user_id})
            SET u.group_id = $new_group_id
            MERGE (g:Group {id: $new_group_id})
            SET g.name = $group_name,
                g.rooms = $rooms, g.roommates = $roommates,
                g.budget = $budget, g.months = $months,
                g.embedding = $embedding
            MERGE (u)-[:MEMBER_OF]->(g)
            WITH g
            UNWIND $parameters AS param
            MERGE (gp:GroupParameter {groupId: $new_group_id, name: param.name})
            SET gp.value = param.value
            MERGE (g)-[:HAS_PARAMETER]->(gp)
        """

        session.run(create_new_group_query,
                   user_id=user_id,
                   new_group_id=new_group_id,
                   group_name=new_group_name,
                   rooms=user_params.get('rooms', 0),
                   roommates=user_params.get('roommates', 0),
                   budget=user_params.get('budget', 0),
                   months=user_params.get('months', 0),
                   embedding=new_vector,
                   parameters=[{'name': p, 'value': user_params.get(p, 0)} for p in PARAMETERS])

        logger.info(f"✓ User {user_id} removed from group {current_group_id}, created new group {new_group_id}")
        log_vector_operation(logger, "Created new single-member group vector", len(new_vector), new_group_id)
        return new_group_id

    except Exception as e:
        logger.error(f"Error removing user {user_id} from group: {e}")
        return None


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
        'vector': group['embedding']
    }


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
    
    return {
        'id': record['id'],
        'name': record['name'],
        **params
    }


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
    logger.info(f"✓ Deleted user {user_id} and all associated data")


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
    logger.info(f"✓ User {user_id} sent join request to group {group_id}")


def approve_join_request(session, group_member_user_id, user_id, max_roommates, caps=None, use_weights=False, weights=None):
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
        raise ValueError(f"User {group_member_user_id} is not in any group")
    
    target_group_id = record['group_id']
    
    # Check if join request exists
    check_request_query = """
        MATCH (u:User {id: $user_id})-[r:JOIN_REQUEST]->(g:Group {id: $group_id})
        RETURN r
    """
    request_result = session.run(check_request_query, user_id=user_id, group_id=target_group_id)
    
    if not request_result.single():
        raise ValueError(f"No join request found from user {user_id} to group {target_group_id}")
    
    # Add user to group
    success = add_user_to_group(session, user_id, target_group_id, caps, use_weights, weights)
    
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
        logger.info(f"✓ Group {target_group_id} marked as inactive (reached max capacity)")
    
    logger.info(f"✓ User {user_id} approved and added to group {target_group_id}")
    return True


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
    
    roommates_count = group_info['parameters'].get('roommates', group_info['member_count'])
    member_ids = [member['id'] for member in group_info['members']]
    
    return {
        'id': group_info['id'],
        'roommates': int(roommates_count),
        'active': active,
        'member_ids': member_ids
    }


def find_similar_users(session, user_id, top_k, caps=None, use_weights=False, weights=None):
    """
    Find similar users based on vector similarity.
    
    Args:
        session: Neo4j session
        user_id: Query user ID
        top_k: Number of similar users to return
        caps: Normalization caps
        use_weights: Whether to use weighted vectors
        weights: Parameter weights
        
    Returns:
        list: List of dicts with user_id and score
    """
    weights = weights or group_parameter_weights
    
    # Get user parameters and create query vector
    user_params = get_user_parameters(session, user_id)
    group_values = {p: user_params.get(p, 0) for p in PARAMETERS}
    
    if use_weights:
        query_vec = create_group_vector_with_weights(group_values, PARAMETERS, weights, caps)
    else:
        query_vec = create_user_vector(group_values, PARAMETERS, caps)
    
    # Find similar groups
    exclude_group_id = f"g_{user_id}"
    similar_groups = find_similar(session, query_vec, top_k=top_k, exclude_id=exclude_group_id)
    
    # Extract user IDs from group results
    results = []
    for group in similar_groups:
        group_id = group['id']
        group_info = get_group_info(session, group_id)
        
        if group_info and group_info['members']:
            # For multi-member groups, return the first member as representative
            # or you could return all members
            member_id = group_info['members'][0]['id']
            results.append({
                'user_id': member_id,
                'score': group['score']
            })
    
    return results


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
        RETURN u.id as user_id,
               coalesce(pr.value, 0) as rooms,
               coalesce(pm.value, 0) as roommates,
               coalesce(pb.value, 0) as budget,
               coalesce(pn.value, 1) as months
    """
    result = session.run(query, group_id=group_id, exclude_user_id=exclude_user_id)
    return [r.data() for r in result]




def check_neo4j_connection():
    """
    Check if Neo4j database is running and accessible.
    Returns True if connection is successful, False otherwise.
    """
    try:
        with get_driver() as driver:
            with driver.session() as session:
                # Simple query to test connection
                result = session.run("RETURN 'Neo4j is running' as message")
                record = result.single()
                if record and record['message'] == 'Neo4j is running':
                    logger.info("✅ Neo4j database connection verified")
                    return True
    except Exception as e:
        logger.error(f"❌ Neo4j database connection failed: {e}")
        return False

    logger.error("❌ Neo4j database connection failed: Unknown error")
    return False



def build_test_db_and_find_recommendations(
    top_k=3,
    use_weights=False,
    caps=None,
    weights=None,
    clear_db_first=True,
    test_users=None,
    verbose=True
):
    """
    Build test database and find top-k roommate recommendations for each user.
    
    Args:
        top_k (int): Number of recommendations per user. Use -1 for all available users.
        use_weights (bool): Whether to use group weighted vectors for similarity calculation.
        caps (dict): Normalization caps for user properties. Default: {'budget': 200000, 'months': 36}
        weights (dict): Group weights for vector components. Default: group_parameter_weights.
        clear_db_first (bool): Whether to clear existing users before inserting test data.
        test_users (list): Custom list of test users. Default: sample_users()
        verbose (bool): Whether to log detailed information about each user's recommendations.
        
    Returns:
        dict: Dictionary mapping user IDs to their recommendation lists.
    """
    # Set defaults
    caps = caps or {'budget': 200000, 'months': 36}  # normalization caps
    weights = weights or group_parameter_weights
    users = test_users or sample_users()
    
    # Handle special case where top_k = -1 means "all users"
    effective_top_k = len(users) - 1 if top_k == -1 else top_k
    
    logger.info(f"🏠 Building test database with {len(users)} users")
    logger.info(f"Configuration: top_k={'all' if top_k == -1 else top_k}, "
               f"weighted={use_weights}, clear_first={clear_db_first}")
    logger.debug(f"Vector normalization caps: {caps}")
    logger.debug(f"Parameters used: {PARAMETERS}")
    logger.debug(f"Weights: {weights if use_weights else 'None (unweighted)'}")

    try:
        with get_driver() as driver:
            with driver.session() as session:
                # Setup database
                logger.info("Setting up database schema...")
                ensure_constraints_and_index(session, dims=len(PARAMETERS))
                
                if clear_db_first:
                    clear_users(session)
                else:
                    logger.info("Skipping database clear - keeping existing data")
                
                upsert_users(session, users, caps=caps, use_weights=use_weights, weights=weights)
                
                top_k_desc = "all available" if top_k == -1 else str(effective_top_k)
                logger.info(f"🔍 Finding {top_k_desc} roommate recommendations for each user")
                
                all_results = {}
                successful_queries = 0
                
                # Find recommendations for each user's GROUP
                for user in users:
                    if verbose:
                        logger.info(f"👤 {user['name']} (ID: {user['id']})")
                        logger.info(f"   Preferences: {user['rooms']} rooms, {user['roommates']} roommates, "
                                  f"₽{user['budget']} budget, {user['months']} months")
                    else:
                        logger.debug(f"Processing user {user['id']}: {user['name']}")
                    
                    # Create group query vector (consistent with database vectors)
                    group_values = {p: user.get(p) for p in PARAMETERS}
                    if use_weights:
                        query_vec = create_group_vector_with_weights(group_values, PARAMETERS, weights, caps)
                    else:
                        query_vec = create_user_vector(group_values, PARAMETERS, caps)
                    
                    # Find similar groups (exclude this user's group)
                    group_id = f"g_{user['id']}"
                    results = find_similar(session, query_vec, top_k=effective_top_k, exclude_id=group_id)
                    all_results[user['id']] = results
                    
                    if results:
                        if verbose:
                            logger.info("   💫 Top recommendations:")
                            for i, r in enumerate(results, 1):
                                similarity_pct = r['score'] * 100
                                logger.info(f"      {i}. {r['name']} (ID: {r['id']}) - {similarity_pct:.1f}% match")
                        successful_queries += 1
                    else:
                        if verbose:
                            logger.warning("   ❌ No recommendations found")
                        else:
                            logger.debug(f"No recommendations found for user {user['id']}")
                
                logger.debug(f"Recommendation generation completed: {successful_queries}/{len(users)} users processed successfully")
                return all_results
                
    except ServiceUnavailable as e:
        logger.error("❌ Neo4j connection failed. Falling back to local similarity computation.")
        logger.error(f"Connection error: {e}")
        logger.info("Switching to local computation mode...")
        
        top_k_desc = "all available" if top_k == -1 else str(effective_top_k)
        logger.info(f"🔍 Finding {top_k_desc} roommate recommendations (local computation)")
        
        all_results = {}
        successful_queries = 0
        
        for user in users:
            if verbose:
                logger.info(f"👤 {user['name']} (ID: {user['id']})")
                logger.info(f"   Preferences: {user['rooms']} rooms, {user['roommates']} roommates, "
                          f"₽{user['budget']} budget, {user['months']} months")
            else:
                logger.debug(f"Processing user {user['id']}: {user['name']}")
            
            results = find_similar_local(users, user, caps=caps, use_weights=use_weights, 
                                       weights=weights, top_k=effective_top_k)
            all_results[user['id']] = results
            
            if results:
                if verbose:
                    logger.info("   💫 Top recommendations:")
                    for i, r in enumerate(results, 1):
                        similarity_pct = r['score'] * 100
                        logger.info(f"      {i}. {r['name']} (ID: {r['id']}) - {similarity_pct:.1f}% match")
                successful_queries += 1
            else:
                if verbose:
                    logger.warning("   ❌ No recommendations found")
                else:
                    logger.debug(f"No recommendations found for user {user['id']}")
            
        logger.debug(f"Local computation completed: {successful_queries}/{len(users)} users processed successfully")
        return all_results
    
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        logger.debug(f"Error details: {type(e).__name__}: {str(e)}")
        return {}

if __name__ == '__main__':
    from simulation import sample_users, simulate_group_formation
    
    logger.info("🎯 Neo4j Roommate Recommendation System Test Suite")
    logger.info("=" * 60)

    # Check Neo4j connection first
    logger.info("🔍 Checking Neo4j database connection...")
    if not check_neo4j_connection():
        logger.error("\n" + "=" * 60)
        logger.error("🚫 NEO4J DATABASE CONNECTION FAILED")
        logger.error("=" * 60)
        logger.error("❌ Unable to connect to Neo4j database.")
        logger.error("")
        logger.error("🔧 TROUBLESHOOTING STEPS:")
        logger.error("   1. Make sure Neo4j Desktop is running")
        logger.error("   2. Ensure your Neo4j instance is started")
        logger.error("   3. Check your .env file has correct NEO4J_URI, NEO4J_USERNAME, and NEO4J_PASSWORD")
        logger.error("   4. Verify the URI format (should be like: bolt://localhost:7687)")
        logger.error("")
        logger.error("📖 For more help, check the Neo4j documentation or contact support.")
        logger.error("=" * 60)
        exit(1)

    # Configuration for tests
    USE_WEIGHTS = True
    MAX_ROOMMATES_PER_GROUP = 5
    SIMULATION_ITERATIONS = 15

    # Clean database before testing
    logger.info("🧹 Starting database cleanup...")
    clean_db()

    logger.info("\n📊 Phase 1: Basic Recommendation System Test")
    logger.info("-" * 50)

    # Build test database and find recommendations
    all_recommendations = build_test_db_and_find_recommendations(
        top_k=-1,
        use_weights=USE_WEIGHTS,
        verbose=False
    )

    logger.info("📈 Basic Test Results:")
    logger.info(f"   Processed {len(all_recommendations)} users")
    total_recommendations = sum(len(recs) for recs in all_recommendations.values())
    logger.info(f"   Generated {total_recommendations} total recommendations")

    if all_recommendations:
        avg_recommendations = total_recommendations / len(all_recommendations)
        logger.info(f"   Average recommendations per user: {avg_recommendations:.1f}")

        # Log some statistics
        recommendation_counts = [len(recs) for recs in all_recommendations.values()]
        max_recs = max(recommendation_counts) if recommendation_counts else 0
        min_recs = min(recommendation_counts) if recommendation_counts else 0
        logger.info(f"   Recommendation range: {min_recs}-{max_recs} per user")

    logger.info("\n🏃 Phase 2: Group Formation Simulation")
    logger.info("-" * 50)

    try:
        with get_driver() as driver:
            with driver.session() as session:
                # Setup database with test users
                logger.info("Setting up database with test users...")
                ensure_constraints_and_index(session, dims=len(PARAMETERS))
                test_users = sample_users()
                upsert_users(session, test_users, use_weights=USE_WEIGHTS)

                # Run the group formation simulation
                simulation_results = simulate_group_formation(
                    session,
                    max_iterations=SIMULATION_ITERATIONS,
                    max_roommates_per_group=MAX_ROOMMATES_PER_GROUP,
                    use_weights=USE_WEIGHTS,
                    verbose=True
                )

                # Analyze group changes
                logger.info("\n📊 Simulation Analysis:")
                logger.info(f"   Total iterations: {simulation_results['iterations']}")
                logger.info(f"   Successful group joins: {simulation_results['successful_joins']}")
                logger.info(f"   Failed join attempts: {simulation_results['failed_joins']}")
                logger.info(f"   Final number of groups: {simulation_results['final_groups']}")
                logger.info(f"   Group changes tracked: {len(simulation_results['group_changes'])}")

                if simulation_results['group_changes']:
                    logger.info("\n🔄 Group Parameter Evolution:")

                    # Show a few examples of how parameters changed
                    for i, change in enumerate(simulation_results['group_changes'][:5]):  # Show first 5 changes
                        logger.info(f"   Change {i+1} (Iteration {change['iteration']}):")
                        logger.info(f"      User {change['user_id']} moved from {change['old_group']} to {change['new_group']}")
                        logger.info(f"      Group size: {change['group_size']} members")
                        logger.info(f"      Parameter changes:")

                        for param in PARAMETERS:
                            old_val = change['old_parameters'].get(param, 0)
                            new_val = change['new_parameters'].get(param, 0)
                            if old_val != new_val:
                                diff = new_val - old_val
                                logger.info(f"         {param}: {old_val} → {new_val} ({'+' if diff > 0 else ''}{diff})")

                    # Show summary of parameter changes if there are many
                    if len(simulation_results['group_changes']) > 5:
                        logger.info(f"   ... and {len(simulation_results['group_changes']) - 5} more changes")

                    # Calculate average group sizes
                    group_sizes = [change['group_size'] for change in simulation_results['group_changes']]
                    if group_sizes:
                        avg_group_size = sum(group_sizes) / len(group_sizes)
                        max_group_size = max(group_sizes)
                        logger.info(f"   Average final group size: {avg_group_size:.1f} members")
                        logger.info(f"   Largest group formed: {max_group_size} members")

                # Show final group distribution
                logger.info("\n🏠 Final Group Distribution:")
                group_size_query = """
                    MATCH (g:Group)
                    RETURN COUNT {(g)<-[:MEMBER_OF]-()} as member_count, count(g) as group_count
                    ORDER BY member_count
                """
                size_result = session.run(group_size_query)
                total_groups = 0
                total_members = 0

                for record in size_result:
                    member_count = record['member_count']
                    group_count = record['group_count']
                    total_groups += group_count
                    total_members += member_count * group_count
                    logger.info(f"   {group_count} groups with {member_count} members")

                if total_groups > 0:
                    avg_members_per_group = total_members / total_groups
                    logger.info(f"   Total: {total_groups} groups, {total_members} members")
                    logger.info(f"   Average: {avg_members_per_group:.1f} members per group")

    except Exception as e:
        logger.error(f"❌ Error during group formation simulation: {e}")
        logger.debug(f"Error details: {type(e).__name__}: {str(e)}")

    logger.info("\n🎉 Test Suite Completed!")
    logger.info("=" * 60)

    # Summary
    if all_recommendations and 'simulation_results' in locals():
        logger.info("📋 Final Summary:")
        logger.info(f"   ✅ Basic recommendation system: Working ({len(all_recommendations)} users)")
        logger.info(f"   ✅ Group formation simulation: Completed ({simulation_results['successful_joins']} joins)")
        logger.info(f"   ✅ Parameter tracking: {len(simulation_results['group_changes'])} changes logged")
    else:
        logger.warning("⚠️  Some tests may have failed or produced incomplete results")

    logger.debug("All test operations completed - system ready for use")
