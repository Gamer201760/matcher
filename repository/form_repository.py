"""
FormRepository implementation for managing user forms.

This repository bridges between the entity layer (Form with Parameters)
and the database layer (Neo4j with limited parameter support).

Current limitations:
- Database only stores 4 parameters: rooms, roommates, budget, months
- Entity.Parameters has 13 fields
- This implementation maps the overlapping fields and uses defaults for others
"""

from uuid import UUID

from neo4j import Driver

from entity.errors import DomainError, NotFoundError
from entity.form import Form
from entity.parameters import Parameters
from infrastructure.neo4j import (
    delete_user_form,
    get_user_form,
    upsert_users,
)
from repository.form_dto import db_form_to_form, parameters_to_db_dict


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
        # TODO: Get rid of caps, they are no longer used by rec system
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
        # Convert Form entity to database format using DTO
        user_dict = parameters_to_db_dict(form.parameters, include_id=str(form.user_id))

        with self.driver.session() as session:
            upsert_users(
                session,
                [user_dict],
            )

        return form.user_id

    def get_by_user_id(self, user_id: UUID) -> Form:
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
                raise NotFoundError(user_id)

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
            raise DomainError(f'Form not found for user {user_id}')

        # Create updated form
        updated_form = Form(
            id=existing_form.id,
            user_id=existing_form.user_id,
            parameters=parameters,
            active=existing_form.active,
            created_at=existing_form.created_at,
        )

        # Update in database using DTO
        user_dict = parameters_to_db_dict(updated_form.parameters, include_id=str(updated_form.user_id))

        with self.driver.session() as session:
            upsert_users(
                session,
                [user_dict],
            )

    def delete_by_user_id(self, user_id: UUID) -> None:
        """
        Delete a form by user ID.

        Args:
            user_id: User ID to delete
        """
        with self.driver.session() as session:
            delete_user_form(session, str(user_id))

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
