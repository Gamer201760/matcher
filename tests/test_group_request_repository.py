"""
Unit tests for GroupRequestRepository

Tests join request lifecycle: creation, retrieval, listing, and deletion.
"""

import unittest
from uuid import uuid4

from repository.recommendation_system.db import (
    check_neo4j_connection,
    clear_users,
    ensure_constraints_and_index,
    get_driver,
)

from entity.form import Form
from entity.parameters import Parameters, Sex, UserType
from entity.point import Point
from repository.form_repository import FormRepository
from repository.group_repository import GroupRepository
from repository.group_request_repository import GroupRequestRepository


class TestGroupRequestRepository(unittest.TestCase):
    """Test suite for GroupRequestRepository."""

    @classmethod
    def setUpClass(cls):
        """Set up test environment once before all tests."""
        # Check Neo4j connection
        if not check_neo4j_connection():
            raise RuntimeError("Neo4j database is not available")

        # Initialize database
        with get_driver() as driver:
            with driver.session() as session:
                ensure_constraints_and_index(session, dims=4)

    def setUp(self):
        """Set up before each test."""
        # Clear database before each test
        with get_driver() as driver:
            with driver.session() as session:
                clear_users(session)

        # Create repository instances
        self.repo = GroupRequestRepository()
        self.form_repo = FormRepository()
        self.group_repo = GroupRepository()

    def tearDown(self):
        """Clean up after each test."""
        if hasattr(self, 'repo'):
            self.repo.close()
        if hasattr(self, 'form_repo'):
            self.form_repo.close()
        if hasattr(self, 'group_repo'):
            self.group_repo.close()

    def _create_test_form(self, user_id=None) -> Form:
        """Helper to create a test form."""
        if user_id is None:
            user_id = uuid4()

        parameters = Parameters(
            name=f"User {user_id}",
            surname="Test",
            geo=Point(55.7558, 37.6173),
            photos=[],
            budget=50000,
            room_count=2,
            roommates_count=1,
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

    def test_01_create_request(self):
        """Test creating a new join request."""
        # Create two users
        form1 = self._create_test_form()
        form2 = self._create_test_form()

        self.form_repo.create(form1)
        self.form_repo.create(form2)

        # Get first user's group
        group1 = self.group_repo.get_by_user_id(form1.user_id)

        # Create join request from user2 to group1
        request_id = self.repo.create(group1.id, form2.user_id)

        # Verify request ID was returned
        self.assertIsNotNone(request_id)

        print(f"✓ Created join request {request_id} from user {form2.user_id} to group {group1.id}")

    def test_02_get_request(self):
        """Test retrieving a join request by ID."""
        # Create two users
        form1 = self._create_test_form()
        form2 = self._create_test_form()

        self.form_repo.create(form1)
        self.form_repo.create(form2)

        # Get first user's group
        group1 = self.group_repo.get_by_user_id(form1.user_id)

        # Create join request
        request_id = self.repo.create(group1.id, form2.user_id)

        # Retrieve the request
        request = self.repo.get(request_id)

        # Verify
        self.assertIsNotNone(request)
        self.assertEqual(request.id, request_id)
        self.assertEqual(request.group_id, group1.id)
        self.assertEqual(request.user_id, form2.user_id)

        print(f"✓ Retrieved join request {request_id}")

    def test_03_get_nonexistent_request(self):
        """Test retrieving a non-existent request returns None."""
        fake_id = uuid4()

        # Try to get non-existent request
        request = self.repo.get(fake_id)

        # Verify None is returned
        self.assertIsNone(request)

        print(f"✓ Correctly returned None for non-existent request {fake_id}")

    def test_04_get_all_requests(self):
        """Test listing all requests for a group."""
        # Create three users
        form1 = self._create_test_form()
        form2 = self._create_test_form()
        form3 = self._create_test_form()

        self.form_repo.create(form1)
        self.form_repo.create(form2)
        self.form_repo.create(form3)

        # Get first user's group
        group1 = self.group_repo.get_by_user_id(form1.user_id)

        # Create two join requests to group1
        request_id1 = self.repo.create(group1.id, form2.user_id)
        request_id2 = self.repo.create(group1.id, form3.user_id)

        # Get all requests for group1
        requests = self.repo.get_all(group1.id)

        # Verify
        self.assertEqual(len(requests), 2)
        request_ids = {r.id for r in requests}
        self.assertIn(request_id1, request_ids)
        self.assertIn(request_id2, request_ids)

        print(f"✓ Retrieved {len(requests)} requests for group {group1.id}")

    def test_05_get_all_empty(self):
        """Test getting all requests for a group with no requests."""
        # Create a user
        form = self._create_test_form()
        self.form_repo.create(form)

        # Get the group
        group = self.group_repo.get_by_user_id(form.user_id)

        # Get all requests (should be empty)
        requests = self.repo.get_all(group.id)

        # Verify
        self.assertEqual(len(requests), 0)

        print(f"✓ Correctly returned empty list for group {group.id} with no requests")

    def test_06_delete_request(self):
        """Test deleting a join request."""
        # Create two users
        form1 = self._create_test_form()
        form2 = self._create_test_form()

        self.form_repo.create(form1)
        self.form_repo.create(form2)

        # Get first user's group
        group1 = self.group_repo.get_by_user_id(form1.user_id)

        # Create join request
        request_id = self.repo.create(group1.id, form2.user_id)

        # Verify it exists
        self.assertIsNotNone(self.repo.get(request_id))

        # Delete the request
        self.repo.delete(request_id)

        # Verify it's gone
        result = self.repo.get(request_id)
        self.assertIsNone(result)

        print(f"✓ Deleted join request {request_id}")

    def test_07_delete_removes_from_list(self):
        """Test that deleting a request removes it from get_all list."""
        # Create three users
        form1 = self._create_test_form()
        form2 = self._create_test_form()
        form3 = self._create_test_form()

        self.form_repo.create(form1)
        self.form_repo.create(form2)
        self.form_repo.create(form3)

        # Get first user's group
        group1 = self.group_repo.get_by_user_id(form1.user_id)

        # Create two requests
        request_id1 = self.repo.create(group1.id, form2.user_id)
        request_id2 = self.repo.create(group1.id, form3.user_id)

        # Verify both exist
        requests_before = self.repo.get_all(group1.id)
        self.assertEqual(len(requests_before), 2)

        # Delete one request
        self.repo.delete(request_id1)

        # Verify only one remains
        requests_after = self.repo.get_all(group1.id)
        self.assertEqual(len(requests_after), 1)
        self.assertEqual(requests_after[0].id, request_id2)

        print("✓ Deleting request correctly updated get_all list")

    def test_08_multiple_groups_requests(self):
        """Test requests to multiple different groups."""
        # Create four users
        forms = [self._create_test_form() for _ in range(4)]
        for form in forms:
            self.form_repo.create(form)

        # Get groups for first two users
        group1 = self.group_repo.get_by_user_id(forms[0].user_id)
        group2 = self.group_repo.get_by_user_id(forms[1].user_id)

        # Create requests from users 3 and 4 to different groups
        req1 = self.repo.create(group1.id, forms[2].user_id)
        req2 = self.repo.create(group2.id, forms[3].user_id)

        # Verify each group has one request
        requests_g1 = self.repo.get_all(group1.id)
        requests_g2 = self.repo.get_all(group2.id)

        self.assertEqual(len(requests_g1), 1)
        self.assertEqual(len(requests_g2), 1)
        self.assertEqual(requests_g1[0].id, req1)
        self.assertEqual(requests_g2[0].id, req2)

        print("✓ Correctly managed requests to multiple groups")

    def test_09_context_manager(self):
        """Test repository works as context manager."""
        # Create two users
        form1 = self._create_test_form()
        form2 = self._create_test_form()

        self.form_repo.create(form1)
        self.form_repo.create(form2)

        group1 = self.group_repo.get_by_user_id(form1.user_id)

        with GroupRequestRepository() as repo:
            request_id = repo.create(group1.id, form2.user_id)
            self.assertIsNotNone(request_id)

        # Verify request was created
        request = self.repo.get(request_id)
        self.assertIsNotNone(request)

        print("✓ Context manager works correctly")


if __name__ == '__main__':
    unittest.main()

