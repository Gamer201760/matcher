"""
Unit tests for GroupRepository

Tests group operations, membership management, and parameter calculations.
"""

import os
import unittest
from uuid import uuid4

from infrastructure.neo4j.connection import (
    check_neo4j_connection,
    ensure_constraints_and_index,
    get_driver,
)
from infrastructure.neo4j.user_ops import clear_users

from entity.form import Form
from entity.group import Group
from entity.parameters import Parameters, Sex, UserType
from entity.point import Point
from repository.form_repository import FormRepository
from repository.group_repository import GroupRepository


class TestGroupRepository(unittest.TestCase):
    """Test suite for GroupRepository."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment once before all tests."""
        # Create driver with credentials from environment variables
        cls.driver = get_driver(
            os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
            os.getenv('NEO4J_USERNAME', 'neo4j'),
            os.getenv('NEO4J_PASSWORD', '123456789'),
        )
        
        # Check Neo4j connection
        if not check_neo4j_connection(cls.driver):
            raise RuntimeError("Neo4j database is not available")
        
        # Initialize database constraints and indexes
        with cls.driver.session() as session:
            from infrastructure.config import VECTOR_DIMENSIONS
            ensure_constraints_and_index(session, dims=VECTOR_DIMENSIONS)

    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests."""
        if hasattr(cls, 'driver'):
            cls.driver.close()

    def setUp(self):
        """Set up before each test."""
        # Clear database before each test
        with self.driver.session() as session:
            clear_users(session)

        # Create repository instances with shared driver
        self.repo = GroupRepository(self.driver)
        self.form_repo = FormRepository(self.driver)

    def tearDown(self):
        """Clean up after each test."""
        # Note: Don't close the driver here, it's shared across tests
        pass

    def _create_test_form(self, user_id=None, budget=50000, rooms=2, roommates=1, month=12) -> Form:
        """Helper to create a test form."""
        if user_id is None:
            user_id = uuid4()

        parameters = Parameters(
            name=f"User {user_id}",
            surname="Test",
            geo=Point(55.7558, 37.6173),
            address="Test Address",
            photos=[],
            budget=budget,
            room_count=rooms,
            roommates_count=roommates,
            month=month,
            age=25,
            smoking=False,
            alko=False,
            pet=False,
            sex=Sex.MALE,
            user_type=UserType.STUDENT,
            description="Test user"
        )

        return Form(
            id=user_id,
            user_id=user_id,
            parameters=parameters
        )

    def _create_test_group(self, group_id=None, budget=50000, rooms=2, roommates=1, month=12) -> Group:
        """Helper to create a test group entity."""
        owner_id = uuid4()
        
        parameters = Parameters(
            name="Test Group",
            surname="",
            geo=Point(55.7558, 37.6173),
            address="",
            photos=[],
            budget=budget,
            room_count=rooms,
            roommates_count=roommates,
            month=month,
            age=0,
            smoking=False,
            alko=False,
            pet=False,
            sex=Sex.MALE,
            user_type=UserType.STUDENT,
            description="Test group"
        )

        # Create group with or without explicit ID
        if group_id is not None:
            group = Group(
                id=group_id,
                owner_id=owner_id,
                parameters=parameters,
                max_users=roommates + 1  # max_users includes owner
            )
        else:
            # Don't pass id parameter to let dataclass default_factory generate it
            group = Group(
                owner_id=owner_id,
                parameters=parameters,
                max_users=roommates + 1  # max_users includes owner
            )
        
        return group

    def test_00_create_empty_group(self):
        """Test creating an empty group without members."""
        # Create a group entity
        group = self._create_test_group(budget=60000, rooms=3, roommates=2, month=12)
        
        # Create the group in database
        created_group_id = self.repo.create(group)
        
        # Verify group was created
        self.assertIsNotNone(created_group_id)
        self.assertEqual(created_group_id, group.id)
        
        # Retrieve the group
        retrieved_group = self.repo.get(created_group_id)
        self.assertIsNotNone(retrieved_group)
        self.assertEqual(retrieved_group.id, created_group_id)
        self.assertEqual(retrieved_group.parameters.budget, 60000)
        self.assertEqual(retrieved_group.parameters.room_count, 3)
        self.assertEqual(retrieved_group.parameters.roommates_count, 2)
        
        # Verify group has no members
        member_count = self.repo.count_members(created_group_id)
        self.assertEqual(member_count, 0)
        
        print(f"✓ Created empty group {created_group_id} with no members")

    def test_00a_create_empty_group_with_auto_id(self):
        """Test creating an empty group without specifying ID (auto-generated)."""
        # Create a group entity without specifying ID
        group = self._create_test_group(group_id=None, budget=45000, rooms=2, roommates=3)
        
        # Create the group in database
        created_group_id = self.repo.create(group)
        
        # Verify group was created with an ID
        self.assertIsNotNone(created_group_id)
        
        # Retrieve the group
        retrieved_group = self.repo.get(created_group_id)
        self.assertIsNotNone(retrieved_group)
        self.assertEqual(retrieved_group.parameters.budget, 45000)
        self.assertEqual(retrieved_group.parameters.room_count, 2)
        
        # Verify group has no members
        member_count = self.repo.count_members(created_group_id)
        self.assertEqual(member_count, 0)
        
        print(f"✓ Created empty group {created_group_id} with auto-generated ID")

    def test_00b_create_empty_group_then_add_user(self):
        """Test creating an empty group and then adding a user to it."""
        # Create an empty group
        group = self._create_test_group(budget=55000, rooms=2, roommates=2)
        created_group_id = self.repo.create(group)
        
        # Verify it's empty
        self.assertEqual(self.repo.count_members(created_group_id), 0)
        
        # Create a user
        form = self._create_test_form(budget=50000, rooms=2, roommates=1)
        self.form_repo.create(form)
        
        # Add user to the empty group
        self.repo.add_user(form.user_id, created_group_id)
        
        # Verify user was added
        member_count = self.repo.count_members(created_group_id)
        self.assertEqual(member_count, 1)
        
        # Verify user is in the correct group
        user_group = self.repo.get_by_user_id(form.user_id)
        self.assertEqual(user_group.id, created_group_id)
        
        print(f"✓ Created empty group {created_group_id} and added user to it")

    def test_00c_create_multiple_empty_groups(self):
        """Test creating multiple empty groups."""
        # Create three empty groups
        group1 = self._create_test_group(budget=30000, rooms=1, roommates=1)
        group2 = self._create_test_group(budget=60000, rooms=2, roommates=2)
        group3 = self._create_test_group(budget=90000, rooms=3, roommates=3)
        
        id1 = self.repo.create(group1)
        id2 = self.repo.create(group2)
        id3 = self.repo.create(group3)
        
        # Verify all were created
        self.assertIsNotNone(id1)
        self.assertIsNotNone(id2)
        self.assertIsNotNone(id3)
        
        # Verify they're different
        self.assertNotEqual(id1, id2)
        self.assertNotEqual(id2, id3)
        self.assertNotEqual(id1, id3)
        
        # Verify all are empty
        self.assertEqual(self.repo.count_members(id1), 0)
        self.assertEqual(self.repo.count_members(id2), 0)
        self.assertEqual(self.repo.count_members(id3), 0)
        
        # Verify parameters are correct
        retrieved1 = self.repo.get(id1)
        retrieved2 = self.repo.get(id2)
        retrieved3 = self.repo.get(id3)
        
        self.assertEqual(retrieved1.parameters.budget, 30000)
        self.assertEqual(retrieved2.parameters.budget, 60000)
        self.assertEqual(retrieved3.parameters.budget, 90000)
        
        print(f"✓ Created 3 empty groups with different parameters")

    def test_00d_create_empty_group_with_zero_params(self):
        """Test creating an empty group with zero/default parameters."""
        # Create a group with zero parameters
        group = self._create_test_group(budget=0, rooms=0, roommates=0, month=0)
        created_group_id = self.repo.create(group)
        
        # Verify group was created
        self.assertIsNotNone(created_group_id)
        
        # Retrieve and verify
        retrieved_group = self.repo.get(created_group_id)
        self.assertIsNotNone(retrieved_group)
        self.assertEqual(retrieved_group.parameters.budget, 0)
        self.assertEqual(retrieved_group.parameters.room_count, 0)
        
        print(f"✓ Created empty group {created_group_id} with zero parameters")

    def test_01_get_group_by_user_id(self):
        """Test getting a group by user ID."""
        # Create a user (which creates a single-member group)
        form = self._create_test_form()
        self.form_repo.create(form)

        # Get the group
        group = self.repo.get_by_user_id(form.user_id)

        # Verify
        self.assertIsNotNone(group)
        self.assertIsNotNone(group.id)
        self.assertEqual(group.parameters.budget, form.parameters.budget)

        print(f"✓ Retrieved group for user {form.user_id}")

    def test_02_get_nonexistent_group(self):
        """Test getting a non-existent group returns None."""
        fake_id = uuid4()

        # Try to get group for non-existent user
        group = self.repo.get_by_user_id(fake_id)

        # Verify None is returned
        self.assertIsNone(group)

        print(f"✓ Correctly returned None for non-existent user {fake_id}")

    def test_03_list_members_single_user(self):
        """Test listing members of a single-member group."""
        # Create a user
        form = self._create_test_form()
        self.form_repo.create(form)

        # Get the group
        group = self.repo.get_by_user_id(form.user_id)

        # List members
        members = self.repo.list_members(group.id)

        # Verify
        self.assertEqual(len(members), 1)
        self.assertEqual(members[0].user_id, form.user_id)

        print(f"✓ Listed 1 member in group {group.id}")

    def test_04_count_members(self):
        """Test counting members in a group."""
        # Create a user
        form = self._create_test_form()
        self.form_repo.create(form)

        # Get the group
        group = self.repo.get_by_user_id(form.user_id)

        # Count members
        count = self.repo.count_members(group.id)

        # Verify
        self.assertEqual(count, 1)

        print(f"✓ Counted {count} member(s) in group {group.id}")

    def test_05_add_user_to_group(self):
        """Test adding a user to an existing group."""
        # Create two users (each in their own group)
        form1 = self._create_test_form()
        form2 = self._create_test_form()

        self.form_repo.create(form1)
        self.form_repo.create(form2)

        # Get first user's group
        group1 = self.repo.get_by_user_id(form1.user_id)

        # Add second user to first user's group
        self.repo.add_user(form2.user_id, group1.id)

        # Verify both users are now in the same group
        group1_after = self.repo.get_by_user_id(form1.user_id)
        group2_after = self.repo.get_by_user_id(form2.user_id)

        self.assertEqual(group1_after.id, group2_after.id)

        # Verify member count
        count = self.repo.count_members(group1.id)
        self.assertEqual(count, 2)

        print(f"✓ Added user {form2.user_id} to group {group1.id}")

    def test_06_remove_user_from_group(self):
        """Test removing a user from a multi-member group."""
        # Create two users
        form1 = self._create_test_form()
        form2 = self._create_test_form()

        self.form_repo.create(form1)
        self.form_repo.create(form2)

        # Add second user to first user's group
        group1 = self.repo.get_by_user_id(form1.user_id)
        self.repo.add_user(form2.user_id, group1.id)

        # Remove second user
        self.repo.rm_user(form2.user_id, group1.id)

        # Verify first user still in original group
        group1_after = self.repo.get_by_user_id(form1.user_id)
        self.assertEqual(group1_after.id, group1.id)

        # Verify second user has a new group
        group2_after = self.repo.get_by_user_id(form2.user_id)
        self.assertNotEqual(group2_after.id, group1.id)

        # Verify member count
        count = self.repo.count_members(group1.id)
        self.assertEqual(count, 1)

        print(f"✓ Removed user {form2.user_id} from group {group1.id}")

    def test_07_remove_user_from_single_member_group_fails(self):
        """Test that removing a user from their single-member group raises error."""
        # Create a user
        form = self._create_test_form()
        self.form_repo.create(form)

        # Get the group
        group = self.repo.get_by_user_id(form.user_id)

        # Try to remove user (should fail)
        with self.assertRaises(RuntimeError):
            self.repo.rm_user(form.user_id, group.id)

        print("✓ Correctly prevented removal from single-member group")

    def test_08_update_parameters(self):
        """Test updating group parameters."""
        # Create a user
        form = self._create_test_form()
        self.form_repo.create(form)

        # Get the group
        group = self.repo.get_by_user_id(form.user_id)

        # Update parameters
        new_params = Parameters(
            name="Updated",
            surname="",
            geo=Point(0, 0),
            address="",
            photos=[],
            budget=75000,
            room_count=3,
            roommates_count=2,
            age=25,
            smoking=False,
            alko=False,
            pet=False,
            sex=Sex.MALE,
            user_type=UserType.STUDENT,
            description=""
        )

        self.repo.update_parameters(group.id, new_params)

        # Retrieve and verify
        updated_group = self.repo.get(group.id)
        self.assertEqual(updated_group.parameters.budget, 75000)
        self.assertEqual(updated_group.parameters.room_count, 3)

        print(f"✓ Updated parameters for group {group.id}")

    def test_09_calculate_params(self):
        """Test recalculating group parameters from members."""
        # Create three users with different parameters
        form1 = self._create_test_form(budget=30000, rooms=1, roommates=1)
        form2 = self._create_test_form(budget=60000, rooms=2, roommates=2)
        form3 = self._create_test_form(budget=90000, rooms=3, roommates=3)

        self.form_repo.create(form1)
        self.form_repo.create(form2)
        self.form_repo.create(form3)

        # Add all to same group
        group1 = self.repo.get_by_user_id(form1.user_id)
        self.repo.add_user(form2.user_id, group1.id)
        self.repo.add_user(form3.user_id, group1.id)

        # Recalculate parameters (should average: budget=60000, rooms=2, roommates=2)
        self.repo.calculate_params(group1.id)

        # Retrieve and verify
        updated_group = self.repo.get(group1.id)

        # Check averaged values (allow for floating point precision)
        self.assertAlmostEqual(updated_group.parameters.budget, 60000, delta=100)
        self.assertAlmostEqual(updated_group.parameters.room_count, 2, delta=0.1)
        self.assertAlmostEqual(updated_group.parameters.roommates_count, 2, delta=0.1)

        print(f"✓ Calculated averaged parameters for group {group1.id}")

    def test_10_delete_group(self):
        """Test deleting a group."""
        # Create a user
        form = self._create_test_form()
        self.form_repo.create(form)

        # Get the group
        group = self.repo.get_by_user_id(form.user_id)

        # Delete the group
        self.repo.delete(group.id)

        # Verify group is gone
        result = self.repo.get(group.id)
        self.assertIsNone(result)

        print(f"✓ Deleted group {group.id}")

    def test_11_context_manager(self):
        """Test repository works as context manager."""
        # Create a user
        form = self._create_test_form()
        self.form_repo.create(form)

        with GroupRepository() as repo:
            group = repo.get_by_user_id(form.user_id)
            self.assertIsNotNone(group)

        print("✓ Context manager works correctly")


if __name__ == '__main__':
    unittest.main()

