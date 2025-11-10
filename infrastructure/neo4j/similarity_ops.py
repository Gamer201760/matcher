"""
Similarity and recommendation operations for Neo4j database.

This module handles:
- Vector similarity search
- Group recommendations
- Test database and simulation functions
"""

from ..config import PARAMETERS, get_parameter_statistics, GROUP_PARAMETER_WEIGHTS
from ..logging_utils import (
    log_neo4j_query,
    log_similarity_results,
    log_vector_operation,
    setup_logger,
)
from recommendation import create_vector, euclidean_distance

# Setup logger
logger = setup_logger('roommate_db', 'INFO')


def find_similar(session, vector, exclude_id, top_k=5):
    """Find similar groups using vector similarity search."""
    log_vector_operation(logger, 'Executing similarity search', len(vector), exclude_id)

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
        'excludeId': exclude_id,
    }
    log_neo4j_query(
        logger,
        similarity_query,
        **params,
    )

    records = session.run(similarity_query, **params)
    results = [r.data() for r in records]

    if exclude_id:
        log_similarity_results(logger, exclude_id, results, top_k)

    return results


def find_similar_local(
    users, query_user, caps=None, use_weights=False, weights=None, top_k=5
):
    """Find similar groups using local computation (fallback method)."""
    weights = weights or GROUP_PARAMETER_WEIGHTS
    query_user_id = query_user.get('id')
    query_group_id = query_user_id

    logger.debug(
        f'Computing local similarity for group {query_group_id} against {len(users)} groups'
    )
    logger.debug(f'Using weights: {use_weights}')

    group_values = {p: query_user.get(p) for p in PARAMETERS}
    qvec = create_vector(
        group_values, 
        PARAMETERS, 
        statistics=get_parameter_statistics(),
        weights=weights if use_weights else None
    )

    log_vector_operation(
        logger, 'Generated group query vector', len(qvec), query_group_id
    )

    results = []
    for u in users:
        uid = u['id']
        gid = uid
        if gid == query_group_id:
            continue

        values = {p: u.get(p) for p in PARAMETERS}
        uvec = create_vector(
            values, 
            PARAMETERS, 
            statistics=get_parameter_statistics(),
            weights=weights if use_weights else None
        )

        # euclidean_distance returns distance; convert to similarity
        distance = euclidean_distance(qvec, uvec)
        sim = 1.0 - distance

        logger.debug(
            f'Similarity between {query_group_id} and {gid}: {sim:.4f} (distance: {distance:.4f})'
        )
        results.append(
            {'id': gid, 'name': f"Group of {u.get('name') or uid}", 'score': sim}
        )

    results.sort(key=lambda r: r['score'], reverse=True)
    final_results = results[:top_k]

    log_similarity_results(logger, query_group_id, final_results, top_k)
    return final_results


def find_similar_users(
    session, user_id, top_k, caps=None, use_weights=False, weights=None
):
    """
    Find similar users based on vector similarity.

    Args:
        session: Neo4j session
        user_id: Query user ID
        top_k: Number of similar users to return
        caps: Deprecated (kept for compatibility)
        use_weights: Whether to use weighted vectors
        weights: Parameter weights

    Returns:
        list: List of dicts with user_id and score
    """
    weights = weights or GROUP_PARAMETER_WEIGHTS

    # Import here to avoid circular dependency
    from .group_ops import get_group_info
    from .user_ops import get_user_parameters

    # Get user parameters and create query vector
    user_params = get_user_parameters(session, user_id)
    group_values = {p: user_params.get(p, 0) for p in PARAMETERS}

    query_vec = create_vector(
        group_values, 
        PARAMETERS, 
        statistics=get_parameter_statistics(),
        weights=weights if use_weights else None
    )

    # Find similar groups
    exclude_group_id = user_id
    similar_groups = find_similar(
        session, query_vec, top_k=top_k, exclude_id=exclude_group_id
    )

    # Extract user IDs from group results
    results = []
    for group in similar_groups:
        group_id = group['id']
        group_info = get_group_info(session, group_id)

        if group_info and group_info['members']:
            # For multi-member groups, return the first member as representative
            # or you could return all members
            member_id = group_info['members'][0]['id']
            results.append({'user_id': member_id, 'score': group['score']})

    return results
