"""
GroupRequestRepository implementation for managing join requests.

This repository handles the lifecycle of group join requests:
creation, retrieval, listing, and deletion.
"""

from uuid import UUID, uuid4
from typing import Optional

from entity.group import GroupRequest
from repository.recommendation_system.db import (
    get_driver,
    send_join_request,
    get_join_request,
    get_all_join_requests,
    delete_join_request,
    create_join_request_with_id,
)


class GroupRequestRepository:
    """
    Repository for group join request operations.
    
    Manages the full lifecycle of join requests between users and groups.
    """
    
    def __init__(self):
        """Initialize GroupRequestRepository with database driver."""
        self.driver = get_driver()
    
    def create(self, group_id: UUID, user_id: UUID) -> UUID:
        """
        Create a new join request from a user to a group.
        
        Args:
            group_id: Target group ID
            user_id: User ID sending the request
            
        Returns:
            UUID: The request ID
        """
        request_id = uuid4()
        
        with self.driver.session() as session:
            # Database stores groups with 'g_' prefix
            db_group_id = f"g_{group_id}"
            # Create the request with our UUID stored as a property
            create_join_request_with_id(session, request_id, str(user_id), db_group_id)
        
        return request_id
    
    def get(self, request_id: UUID) -> Optional[GroupRequest]:
        """
        Get a single join request by ID.
        
        Args:
            request_id: Request ID to look up
            
        Returns:
            GroupRequest entity if found, None otherwise
        """
        with self.driver.session() as session:
            db_request = get_join_request(session, str(request_id))
            
            if not db_request:
                return None
            
            return self._db_dict_to_request(db_request)
    
    def get_all(self, group_id: UUID) -> list[GroupRequest]:
        """
        Get all join requests for a specific group.
        
        Args:
            group_id: Group ID
            
        Returns:
            list[GroupRequest]: List of join requests
        """
        with self.driver.session() as session:
            # Database stores groups with 'g_' prefix
            db_group_id = f"g_{group_id}"
            db_requests = get_all_join_requests(session, db_group_id)
            
            return [self._db_dict_to_request(req) for req in db_requests]
    
    def delete(self, request_id: UUID) -> None:
        """
        Delete a join request by its ID.
        
        Args:
            request_id: Request ID to delete
        """
        with self.driver.session() as session:
            delete_join_request(session, str(request_id))
    
    def _db_dict_to_request(self, db_dict: dict) -> GroupRequest:
        """
        Convert database dictionary to GroupRequest entity.
        
        Args:
            db_dict: Dictionary from database
            
        Returns:
            GroupRequest: GroupRequest entity
        """
        # Parse request ID - stored as UUID string property
        request_id = db_dict['id']
        if isinstance(request_id, str):
            request_id = UUID(request_id)
        
        # Parse user ID
        user_id = db_dict['user_id']
        if isinstance(user_id, str):
            user_id = UUID(user_id)
        
        # Parse group ID - remove 'g_' prefix if present
        group_id = db_dict['group_id']
        if isinstance(group_id, str):
            clean_group_id = group_id.replace('g_', '', 1) if group_id.startswith('g_') else group_id
            group_id = UUID(clean_group_id)
        
        return GroupRequest(
            id=request_id,
            group_id=group_id,
            user_id=user_id,
            created_at=db_dict.get('timestamp')
        )
    
    def close(self):
        """Close the database driver."""
        if self.driver:
            self.driver.close()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

