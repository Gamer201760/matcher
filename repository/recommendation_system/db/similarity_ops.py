"""
Similarity and recommendation operations for Neo4j database.

This module handles:
- Vector similarity search
- Group recommendations
- Test database and simulation functions
"""

from neo4j.exceptions import ServiceUnavailable

from ..user_vector_utils import (
    create_user_vector,
    create_group_vector_with_weights,
    group_parameter_weights,
    euclidean_distance,
)
from ..logging_utils import (
    setup_logger,
    log_neo4j_query,
    log_vector_operation,
    log_similarity_results,
)
from ..config import PARAMETERS

# Setup logger
logger = setup_logger("roommate_db", "INFO")


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
    
    # Import here to avoid circular dependency
    from .user_ops import get_user_parameters
    from .group_ops import get_group_info
    
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
    from .connection import get_driver, ensure_constraints_and_index
    from .user_ops import upsert_users, clear_users
    
    # Set defaults
    caps = caps or {'budget': 200000, 'months': 36}  # normalization caps
    weights = weights or group_parameter_weights
    
    # Import simulation module only when needed
    from ..simulation import sample_users
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

