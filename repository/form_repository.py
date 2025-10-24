"""
FormRepository implementation for managing user forms.

This repository bridges between the entity layer (Form with Parameters)
and the database layer (Neo4j with limited parameter support).

Current limitations:
- Database only stores 4 parameters: rooms, roommates, budget, months
- Entity.Parameters has 13 fields
- This implementation maps the overlapping fields and uses defaults for others
"""

from typing import Optional
from uuid import UUID

from neo4j import Driver

from entity.form import Form
from entity.parameters import Parameters
from repository.form_dto import db_form_to_form
from repository.recommendation_system.db import (
    delete_user_form,
    get_user_form,
    upsert_users,
)


class FormRepository:
    """
    Repository for user form CRUD operations.

    Maps between entity.Form (with full Parameters) and the database
    representation (limited to 4 fields: rooms, roommates, budget, months).
    """

    def __init__(self, driver: Driver, caps=None, use_weights=False, weights=None):
        """
        Initialize FormRepository with database configuration.

        Args:
            caps: Normalization caps for vector creation
            use_weights: Whether to use weighted vectors
            weights: Parameter weights for group vector creation
        """
        self.driver = driver
        self.caps = caps or {'budget': 200000, 'months': 36}
        self.use_weights = use_weights
        self.weights = weights

    def create(self, form: Form) -> UUID:
        """
        Create a new user form in the database.

        Args:
            form: Form entity to create

        Returns:
            UUID: The user_id of the created form
        """
        # Convert Form entity to database format
        user_dict = self._form_to_db_dict(form)

        with self.driver.session() as session:
            upsert_users(
                session,
                [user_dict],
                caps=self.caps,
                use_weights=self.use_weights,
                weights=self.weights,
            )

        return form.user_id

    def get_by_user_id(self, user_id: UUID) -> Optional[Form]:
        """
        Retrieve a form by user ID.

        Args:
            user_id: User ID to look up

        Returns:
            Form entity if found, None otherwise
        """
        with self.driver.session() as session:
            db_form = get_user_form(session, str(user_id))

            if not db_form:
                return None

            return db_form_to_form(db_form, user_id)

    def update_parameters_by_user_id(
        self, user_id: UUID, parameters: Parameters
    ) -> None:
        """
        Update form parameters for a user.

        Args:
            user_id: User ID to update
            parameters: New parameters
        """
        # Get existing form to preserve id and metadata
        existing_form = self.get_by_user_id(user_id)
        if not existing_form:
            raise ValueError(
                f'Form not found for user {user_id}'
            )  # TODO: refactor to internal error

        # Create updated form
        updated_form = Form(
            id=existing_form.id,
            user_id=user_id,
            parameters=parameters,
            active=existing_form.active,
            created_at=existing_form.created_at,
        )

        # Update in database
        user_dict = self._form_to_db_dict(updated_form)

        with self.driver.session() as session:
            upsert_users(
                session,
                [user_dict],
                caps=self.caps,
                use_weights=self.use_weights,
                weights=self.weights,
            )

    def delete_by_user_id(self, user_id: UUID) -> None:
        """
        Delete a form by user ID.

        Args:
            user_id: User ID to delete
        """
        with self.driver.session() as session:
            delete_user_form(session, str(user_id))

    def _form_to_db_dict(self, form: Form) -> dict:
        """
        Convert Form entity to database dictionary format.

        Maps:
        - parameters.room_count -> rooms
        - parameters.roommates_count -> roommates
        - parameters.budget -> budget
        - Default: months = 12

        Args:
            form: Form entity

        Returns:
            dict: Database-compatible dictionary
        """
        params = form.parameters

        return {
            'id': str(form.user_id),
            'name': params.name if params.name else f'User {form.user_id}',
            'rooms': params.room_count,
            'roommates': params.roommates_count,
            'budget': params.budget,
            'months': 12,  # Default value, not in Parameters entity
        }

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
