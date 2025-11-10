"""
GroupRepository implementation for managing groups and membership.

This repository provides group CRUD operations, member management,
and parameter calculations using Neo4j database functions.
"""

from uuid import UUID

from neo4j import Driver

from entity.errors import DomainError, NotFoundError
from entity.form import Form
from entity.group import Group
from entity.parameters import Parameters
from infrastructure.neo4j import (
    add_user_to_group,
    change_group_owner,
    count_group_members,
    delete_group,
    delete_group_by_owner,
    get_group_by_owner_id,
    get_group_by_user_id,
    get_group_info,
    get_group_member_parameters,
    list_group_members,
    remove_user_from_group,
    update_group_parameters,
)
from repository.form_dto import db_form_to_form
from repository.group_dto import db_group_to_group


class GroupRepository:
    """
    Repository for group management operations.

    Handles groups, membership, ownership, and parameter calculations.
    """

    def __init__(self, driver: Driver, caps=None, use_weights=False, weights=None):
        """
        Initialize GroupRepository with database configuration.

        Args:
            caps: Normalization caps for vector creation
            use_weights: Whether to use weighted vectors
            weights: Parameter weights for group vector creation
        """
        self.driver = driver
        self.caps = caps or {'budget': 200000, 'months': 36}
        self.use_weights = use_weights
        self.weights = weights

    def create(self, group: Group) -> UUID:
        """
        Create a new group in the database.

        Note: In current implementation, groups are created automatically
        when users are created. This method is primarily for explicit group creation.

        Args:
            group: Group entity to create

        Returns:
            UUID: The group_id of the created group
        """
        # TODO: Implement explicit group creation when needed
        # For now, groups are created via user creation (single-member groups)
        # or via join operations (multi-member groups)
        raise NotImplementedError(
            'Explicit group creation not yet implemented. '
            'Groups are created automatically via user/form creation.'
        )

    def get(self, group_id: UUID) -> Group:
        """
        Retrieve a group by ID.

        Args:
            group_id: Group ID to look up

        Returns:
            Group entity if found, None otherwise
        """
        with self.driver.session() as session:
            # Database stores groups with 'g_' prefix
            db_group_id = group_id
            db_group = get_group_info(session, db_group_id)

            if not db_group:
                raise NotFoundError(group_id)

            return db_group_to_group(db_group, group_id)

    def get_by_user_id(self, user_id: UUID) -> Group:
        """
        Get the group that a user is a member of.

        Args:
            user_id: User ID

        Returns:
            Group entity if found, None otherwise
        """
        with self.driver.session() as session:
            db_group = get_group_by_user_id(session, str(user_id))

            if not db_group:
                raise NotFoundError(user_id)

            # Extract group_id from the returned group info
            group_id_str = db_group.get('id')
            if not group_id_str:
                raise DomainError('db group not found id')

            # Parse group ID using robust helper
            return db_group_to_group(db_group, self._parse_group_id(group_id_str))

    def get_by_owner_id(self, owner_id: UUID) -> Group:
        """
        Get the group owned by a specific user.

        Args:
            owner_id: Owner user ID

        Returns:
            Group entity if found, None otherwise
        """
        with self.driver.session() as session:
            db_group = get_group_by_owner_id(session, str(owner_id))

            if not db_group:
                raise NotFoundError(owner_id)

            group_id_str = db_group.get('id')
            if not group_id_str:
                raise DomainError('db group not found id')

            return db_group_to_group(db_group, self._parse_group_id(group_id_str))

    def update_parameters(self, group_id: UUID, parameters: Parameters) -> None:
        """
        Update group parameters and recalculate group vector.

        Args:
            group_id: Group ID to update
            parameters: New parameters
        """
        params_dict = {
            'rooms': parameters.room_count,
            'roommates': parameters.roommates_count,
            'budget': parameters.budget,
            'months': 12,  # Default value
        }

        with self.driver.session() as session:
            # Database stores groups with 'g_' prefix
            db_group_id = group_id
            update_group_parameters(
                session,
                db_group_id,
                params_dict,
                caps=self.caps,
                use_weights=self.use_weights,
                weights=self.weights,
            )

    def delete(self, group_id: UUID) -> None:
        """
        Delete a group by its ID.

        Args:
            group_id: Group ID to delete
        """
        with self.driver.session() as session:
            # Database stores groups with 'g_' prefix
            db_group_id = group_id
            delete_group(session, db_group_id)

    def delete_by_owner_id(self, owner_id: UUID) -> None:
        """
        Delete a group owned by a specific user.

        Args:
            owner_id: Owner user ID
        """
        with self.driver.session() as session:
            delete_group_by_owner(session, str(owner_id))

    def list_members(self, group_id: UUID) -> list[Form]:
        """
        List all members of a group as Form entities.

        Args:
            group_id: Group ID

        Returns:
            list[Form]: List of member forms
        """
        with self.driver.session() as session:
            # Database stores groups with 'g_' prefix
            db_group_id = group_id
            db_members = list_group_members(session, db_group_id)

            forms = []
            for member_dict in db_members:
                user_id = UUID(member_dict['id'])
                forms.append(db_form_to_form(member_dict, user_id))

            return forms

    def count_members(self, group_id: UUID) -> int:
        """
        Count the number of members in a group.

        Args:
            group_id: Group ID

        Returns:
            int: Number of members
        """
        with self.driver.session() as session:
            # Database stores groups with 'g_' prefix
            db_group_id = group_id
            return count_group_members(session, db_group_id)

    def add_user(self, user_id: UUID, group_id: UUID) -> None:
        """
        Add a user to a group.

        Args:
            user_id: User ID to add
            group_id: Target group ID
        """
        with self.driver.session() as session:
            # Database stores groups with 'g_' prefix
            db_group_id = group_id
            success = add_user_to_group(
                session,
                str(user_id),
                db_group_id,
                caps=self.caps,
                use_weights=self.use_weights,
                weights=self.weights,
            )

            if not success:
                raise RuntimeError(f'Failed to add user {user_id} to group {group_id}')

    def rm_user(self, user_id: UUID, group_id: UUID) -> None:
        """
        Remove a user from a group.

        Note: In the current implementation, remove_user_from_group doesn't
        take a group_id parameter - it removes the user from their current group
        and creates a new single-member group.

        Args:
            user_id: User ID to remove
            group_id: Group ID (not used in current implementation)
        """
        with self.driver.session() as session:
            try:
                remove_user_from_group(
                    session,
                    str(user_id),
                    caps=self.caps,
                    use_weights=self.use_weights,
                    weights=self.weights,
                )
            except ValueError as e:
                # Re-raise as RuntimeError for consistency
                raise RuntimeError(str(e))

    def calculate_params(self, group_id: UUID) -> None:
        """
        Recalculate group parameters from member parameters.

        This averages all member parameters and updates the group vector.

        Args:
            group_id: Group ID to recalculate
        """
        with self.driver.session() as session:
            # Database stores groups with 'g_' prefix
            db_group_id = group_id

            # Get all member parameters
            members = get_group_member_parameters(session, db_group_id)

            if not members:
                raise ValueError(
                    f'No members found in group {group_id}'
                )  # TODO: refactor to internal error

            # Calculate averages
            avg_params: dict[str, float] = {
                'rooms': 0,
                'roommates': 0,
                'budget': 0,
                'months': 0,
            }

            for member in members:
                avg_params['rooms'] += member.get('rooms', 0)
                avg_params['roommates'] += member.get('roommates', 0)
                avg_params['budget'] += member.get('budget', 0)
                avg_params['months'] += member.get('months', 0)

            count = len(members)
            for key, _ in avg_params:
                avg_params[key] = avg_params[key] / count

            # Update group with calculated parameters
            update_group_parameters(
                session,
                db_group_id,
                avg_params,
                caps=self.caps,
                use_weights=self.use_weights,
                weights=self.weights,
            )

    def change_owner(self, group_id: UUID, new_owner_id: UUID) -> None:
        """
        Transfer ownership of a group to a new owner.

        Args:
            group_id: Group ID
            new_owner_id: New owner user ID
        """
        with self.driver.session() as session:
            change_group_owner(session, str(group_id), str(new_owner_id))

    def _parse_group_id(self, group_id_str: str) -> UUID:
        """
        Parse group ID from database format to UUID.

        Handles both formats:
        - '{uuid}' -> uses UUID directly as group ID
        - plain UUID string -> converts to UUID

        Args:
            group_id_str: Group ID string from database

        Returns:
            UUID: Parsed UUID

        Raises:
            ValueError: If string cannot be parsed as UUID
        """
        if not group_id_str:
            raise ValueError('Empty group ID')  # TODO: refactor to internal error

        # Remove 'g_' prefix if present
        clean_id = (
            group_id_str.replace('g_', '', 1)
            if group_id_str.startswith('g_')
            else group_id_str
        )

        try:
            return UUID(clean_id)
        except ValueError as e:
            raise ValueError(
                f'Invalid group ID format: {group_id_str}'
            ) from e  # TODO: refactor to use internal error

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
