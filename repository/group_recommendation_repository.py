"""
GroupRecommendationRepository implementation for finding similar groups.

This repository uses vector similarity search to recommend compatible groups
based on averaged member parameters.
"""

from uuid import UUID

from neo4j import Driver

from entity.group import Group
from repository.group_dto import db_dict_to_group
from repository.recommendation_system.config import PARAMETERS
from repository.recommendation_system.db import (
    find_similar,
    get_group_info,
    get_group_member_parameters,
)
from repository.recommendation_system.logging_utils import setup_logger
from repository.recommendation_system.user_vector_utils import (
    create_group_vector_with_weights,
    create_user_vector,
    group_parameter_weights,
)

logger = setup_logger()


class GroupRecommendationRepository:
    """
    Repository for group recommendation operations.

    Finds similar groups using vector similarity search on averaged
    member parameters.
    """

    def __init__(
        self, driver: Driver, caps=None, use_weights=False, weights=None, top_k=5
    ):
        """
        Initialize GroupRecommendationRepository with search configuration.

        Args:
            caps: Normalization caps for vector creation
            use_weights: Whether to use weighted vectors
            weights: Parameter weights for group vector creation
            top_k: Number of recommendations to return
        """
        self.driver = driver
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
            db_group_id = f'g_{group_id}'

            # Get the group's members and calculate average parameters
            members = get_group_member_parameters(session, db_group_id)

            if not members:
                return []

            # Calculate averaged parameters for the query group
            avg_params = self._calculate_average_parameters(members)

            # Create query vector
            if self.use_weights:
                query_vector = create_group_vector_with_weights(
                    avg_params, PARAMETERS, self.weights, self.caps
                )
            else:
                query_vector = create_user_vector(avg_params, PARAMETERS, self.caps)

            # Find similar groups
            similar_groups = find_similar(
                session, query_vector, top_k=self.top_k, exclude_id=db_group_id
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
                        clean_id = (
                            similar_group_id.replace('g_', '', 1)
                            if similar_group_id.startswith('g_')
                            else similar_group_id
                        )
                        parsed_id = UUID(clean_id)
                    except ValueError:  # TODO: refactor to internal error
                        # Skip groups with invalid IDs
                        logger.warning(
                            f'Skipping group with invalid ID format: {similar_group_id}'
                        )
                        continue

                    group_entity = db_dict_to_group(db_group, parsed_id)
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

        avg_params: dict[str, float] = {param: 0 for param in PARAMETERS}

        for member in members:
            for param in PARAMETERS:
                avg_params[param] += member.get(param, 0)

        count = len(members)
        for param, _ in avg_params:
            avg_params[param] = avg_params[param] / count

        return avg_params

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
