"""
GroupRecommendationRepository implementation for finding similar groups.

This repository uses vector similarity search to recommend compatible groups
based on averaged member parameters.
"""

from uuid import UUID
from typing import Optional

from entity.group import Group
from entity.parameters import Parameters, Sex, UserType
from entity.point import Point
from repository.recommendation_system.db import (
    get_driver,
    get_group_info,
    find_similar,
    get_group_member_parameters,
)
from repository.recommendation_system.user_vector_utils import (
    create_user_vector,
    create_group_vector_with_weights,
    group_parameter_weights,
)
from repository.recommendation_system.config import PARAMETERS


class GroupRecommendationRepository:
    """
    Repository for group recommendation operations.
    
    Finds similar groups using vector similarity search on averaged
    member parameters.
    """
    
    def __init__(self, caps=None, use_weights=False, weights=None, top_k=5):
        """
        Initialize GroupRecommendationRepository with search configuration.
        
        Args:
            caps: Normalization caps for vector creation
            use_weights: Whether to use weighted vectors
            weights: Parameter weights for group vector creation
            top_k: Number of recommendations to return
        """
        self.driver = get_driver()
        self.caps = caps or {'budget': 200000, 'months': 36}
        self.use_weights = use_weights
        self.weights = weights or group_parameter_weights
        self.top_k = top_k
    
    def execute(self, group_id: UUID) -> list[Group]:
        """
        Find similar groups to the given group.
        
        Takes the averaged parameters of all members in the group,
        creates a vector, and finds the most similar groups based
        on their averaged parameters.
        
        Args:
            group_id: Group ID to find recommendations for
            
        Returns:
            list[Group]: List of recommended groups, sorted by similarity
        """
        with self.driver.session() as session:
            # Database stores groups with 'g_' prefix
            db_group_id = f"g_{group_id}"
            
            # Get the group's members and calculate average parameters
            members = get_group_member_parameters(session, db_group_id)
            
            if not members:
                return []
            
            # Calculate averaged parameters for the query group
            avg_params = self._calculate_average_parameters(members)
            
            # Create query vector
            if self.use_weights:
                query_vector = create_group_vector_with_weights(
                    avg_params,
                    PARAMETERS,
                    self.weights,
                    self.caps
                )
            else:
                query_vector = create_user_vector(
                    avg_params,
                    PARAMETERS,
                    self.caps
                )
            
            # Find similar groups
            similar_groups = find_similar(
                session,
                query_vector,
                top_k=self.top_k,
                exclude_id=db_group_id
            )
            
            # Convert to Group entities
            result_groups = []
            for similar in similar_groups:
                similar_group_id = similar['id']
                
                # Get full group info
                db_group = get_group_info(session, similar_group_id)
                if db_group:
                    # Parse group ID robustly
                    try:
                        clean_id = similar_group_id.replace('g_', '', 1) if similar_group_id.startswith('g_') else similar_group_id
                        parsed_id = UUID(clean_id)
                    except ValueError:
                        # Skip groups with invalid IDs
                        logger.warning(f"Skipping group with invalid ID format: {similar_group_id}")
                        continue
                    
                    group_entity = self._db_dict_to_group(db_group, parsed_id)
                    result_groups.append(group_entity)
            
            return result_groups
    
    def _calculate_average_parameters(self, members: list[dict]) -> dict:
        """
        Calculate average parameters from a list of member parameter dicts.
        
        Args:
            members: List of member parameter dictionaries
            
        Returns:
            dict: Averaged parameters
        """
        if not members:
            return {}
        
        avg_params = {param: 0 for param in PARAMETERS}
        
        for member in members:
            for param in PARAMETERS:
                avg_params[param] += member.get(param, 0)
        
        count = len(members)
        for param in avg_params:
            avg_params[param] = avg_params[param] / count
        
        return avg_params
    
    def _db_dict_to_group(self, db_dict: dict, group_id: UUID) -> Group:
        """
        Convert database dictionary to Group entity.
        
        Args:
            db_dict: Dictionary from database
            group_id: Group ID
            
        Returns:
            Group: Group entity
        """
        # Extract parameters
        params_dict = db_dict.get('parameters', {})
        
        parameters = Parameters(
            name=db_dict.get('name', ''),
            surname='',
            geo=Point(0.0, 0.0),
            photos=[],
            budget=params_dict.get('budget', 0),
            room_count=params_dict.get('rooms', 0),
            roommates_count=params_dict.get('roommates', 0),
            age=0,
            smoking=False,
            alko=False,
            pet=False,
            sex=Sex.MALE,
            user_type=UserType.STUDENT,
            description='',
        )
        
        # Extract owner_id - in current impl, first member is typically owner
        members = db_dict.get('members', [])
        owner_id = UUID(members[0]['id']) if members else group_id
        
        # Extract max_users from roommates parameter
        max_users = params_dict.get('roommates', 4)
        
        return Group(
            id=group_id,
            owner_id=owner_id,
            parameters=parameters,
            max_users=int(max_users),
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

