"""
Database operations package for Neo4j.

This package provides all database operations split across focused modules:
- connection: Database driver, constraints, and infrastructure
- user_ops: User and form CRUD operations
- group_ops: Group operations and membership management
- request_ops: Join request management
- similarity_ops: Vector similarity search and recommendations

This __init__.py re-exports all functions for backwards compatibility with
code that imports from db_management_utils.
"""

# Connection and infrastructure
# Re-export PARAMETERS constant for convenience
from ..config import PARAMETERS
from .connection import (
    check_neo4j_connection,
    clean_db,
    ensure_constraints_and_index,
    get_driver,
)

# Group operations
from .group_ops import (
    add_user_to_group,
    change_group_owner,
    count_group_members,
    delete_group,
    delete_group_by_owner,
    get_group_by_owner_id,
    get_group_by_user_id,
    get_group_info,
    get_group_member_parameters,
    get_group_with_status,
    list_group_members,
    remove_user_from_group,
    update_group_parameters,
)

# Request operations
from .request_ops import (
    approve_join_request,
    create_join_request_with_id,
    delete_join_request,
    get_all_join_requests,
    get_join_request,
    send_join_request,
)

# Similarity operations
from .similarity_ops import (
    build_test_db_and_find_recommendations,
    find_similar,
    find_similar_local,
    find_similar_users,
)

# User operations
from .user_ops import (
    clear_users,
    delete_user_form,
    get_user_form,
    get_user_parameters,
    upsert_users,
)

__all__ = [
    # Connection
    'get_driver',
    'ensure_constraints_and_index',
    'clean_db',
    'check_neo4j_connection',
    # User ops
    'clear_users',
    'upsert_users',
    'get_user_form',
    'delete_user_form',
    'get_user_parameters',
    # Group ops
    'add_user_to_group',
    'remove_user_from_group',
    'get_group_info',
    'get_group_with_status',
    'get_group_member_parameters',
    'get_group_by_user_id',
    'get_group_by_owner_id',
    'list_group_members',
    'count_group_members',
    'update_group_parameters',
    'change_group_owner',
    'delete_group',
    'delete_group_by_owner',
    # Request ops
    'send_join_request',
    'approve_join_request',
    'get_join_request',
    'get_all_join_requests',
    'delete_join_request',
    'create_join_request_with_id',
    # Similarity ops
    'find_similar',
    'find_similar_local',
    'find_similar_users',
    'build_test_db_and_find_recommendations',
    # Config
    'PARAMETERS',
]

