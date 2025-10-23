"""
Unit tests for FormRepository

Tests form CRUD operations with Neo4j database.
"""

import unittest
from uuid import uuid4

from repository.form_repository import FormRepository
from repository.recommendation_system.db import (
    check_neo4j_connection,
    clear_users,
    get_driver,
    ensure_constraints_and_index,
)
from entity.form import Form
from entity.parameters import Parameters, Sex, UserType
from entity.point import Point


class TestFormRepository(unittest.TestCase):
    """Test suite for FormRepository."""
    
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
        
        # Create repository instance
        self.repo = FormRepository()
    
    def tearDown(self):
        """Clean up after each test."""
        if hasattr(self, 'repo'):
            self.repo.close()
    
    def _create_test_form(self, user_id=None) -> Form:
        """Helper to create a test form."""
        if user_id is None:
            user_id = uuid4()
        
        parameters = Parameters(
            name="Test User",
            surname="Test Surname",
            geo=Point(55.7558, 37.6173),  # Moscow
            photos=["photo1.jpg", "photo2.jpg"],
            budget=50000,
            room_count=2,
            roommates_count=1,
            age=25,
            smoking=False,
            alko=False,
            pet=True,
            sex=Sex.MALE,
            user_type=UserType.STUDENT,
            description="Looking for a quiet roommate"
        )
        
        return Form(
            id=user_id,
            user_id=user_id,
            parameters=parameters
        )
    
    def test_01_create_form(self):
        """Test creating a new form."""
        form = self._create_test_form()
        
        # Create form
        result_id = self.repo.create(form)
        
        # Verify result
        self.assertEqual(result_id, form.user_id)
        
        # Verify form was created in database
        retrieved_form = self.repo.get_by_user_id(form.user_id)
        self.assertIsNotNone(retrieved_form)
        self.assertEqual(retrieved_form.user_id, form.user_id)
        self.assertEqual(retrieved_form.parameters.budget, form.parameters.budget)
        self.assertEqual(retrieved_form.parameters.room_count, form.parameters.room_count)
        self.assertEqual(retrieved_form.parameters.roommates_count, form.parameters.roommates_count)
        
        print(f"✓ Created form for user {form.user_id}")
    
    def test_02_get_by_user_id(self):
        """Test retrieving a form by user ID."""
        # Create a form
        form = self._create_test_form()
        self.repo.create(form)
        
        # Retrieve the form
        retrieved = self.repo.get_by_user_id(form.user_id)
        
        # Verify
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.user_id, form.user_id)
        self.assertEqual(retrieved.parameters.name, form.parameters.name)
        self.assertEqual(retrieved.parameters.budget, form.parameters.budget)
        
        print(f"✓ Retrieved form for user {form.user_id}")
    
    def test_03_get_nonexistent_form(self):
        """Test retrieving a non-existent form returns None."""
        fake_id = uuid4()
        
        # Try to retrieve non-existent form
        result = self.repo.get_by_user_id(fake_id)
        
        # Verify None is returned
        self.assertIsNone(result)
        
        print(f"✓ Correctly returned None for non-existent user {fake_id}")
    
    def test_04_update_parameters(self):
        """Test updating form parameters."""
        # Create initial form
        form = self._create_test_form()
        self.repo.create(form)
        
        # Update parameters
        new_parameters = Parameters(
            name="Updated User",
            surname="Updated Surname",
            geo=Point(55.7558, 37.6173),
            photos=[],
            budget=75000,  # Changed
            room_count=3,  # Changed
            roommates_count=2,  # Changed
            age=26,
            smoking=False,
            alko=True,
            pet=False,
            sex=Sex.MALE,
            user_type=UserType.WORKER,
            description="Updated description"
        )
        
        self.repo.update_parameters_by_user_id(form.user_id, new_parameters)
        
        # Retrieve and verify
        updated = self.repo.get_by_user_id(form.user_id)
        self.assertEqual(updated.parameters.budget, 75000)
        self.assertEqual(updated.parameters.room_count, 3)
        self.assertEqual(updated.parameters.roommates_count, 2)
        
        print(f"✓ Updated parameters for user {form.user_id}")
    
    def test_05_update_nonexistent_form(self):
        """Test updating a non-existent form raises error."""
        fake_id = uuid4()
        
        new_parameters = Parameters(
            name="Test",
            surname="Test",
            geo=Point(0.0, 0.0),
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
            description=""
        )
        
        # Should raise ValueError
        with self.assertRaises(ValueError):
            self.repo.update_parameters_by_user_id(fake_id, new_parameters)
        
        print(f"✓ Correctly raised error for updating non-existent user {fake_id}")
    
    def test_06_delete_form(self):
        """Test deleting a form."""
        # Create form
        form = self._create_test_form()
        self.repo.create(form)
        
        # Verify it exists
        self.assertIsNotNone(self.repo.get_by_user_id(form.user_id))
        
        # Delete the form
        self.repo.delete_by_user_id(form.user_id)
        
        # Verify it's gone
        result = self.repo.get_by_user_id(form.user_id)
        self.assertIsNone(result)
        
        print(f"✓ Deleted form for user {form.user_id}")
    
    def test_07_delete_nonexistent_form(self):
        """Test deleting a non-existent form doesn't raise error."""
        fake_id = uuid4()
        
        # Should not raise error
        try:
            self.repo.delete_by_user_id(fake_id)
            success = True
        except Exception as e:
            success = False
            print(f"Unexpected error: {e}")
        
        self.assertTrue(success)
        print(f"✓ Gracefully handled deletion of non-existent user {fake_id}")
    
    def test_08_multiple_forms(self):
        """Test creating and managing multiple forms."""
        forms = [self._create_test_form() for _ in range(3)]
        
        # Create all forms
        for form in forms:
            self.repo.create(form)
        
        # Verify all exist
        for form in forms:
            retrieved = self.repo.get_by_user_id(form.user_id)
            self.assertIsNotNone(retrieved)
            self.assertEqual(retrieved.user_id, form.user_id)
        
        print(f"✓ Created and verified {len(forms)} forms")
    
    def test_09_context_manager(self):
        """Test repository works as context manager."""
        form = self._create_test_form()
        
        with FormRepository() as repo:
            result_id = repo.create(form)
            self.assertEqual(result_id, form.user_id)
        
        # Verify form was created even after context exit
        retrieved = self.repo.get_by_user_id(form.user_id)
        self.assertIsNotNone(retrieved)
        
        print("✓ Context manager works correctly")


if __name__ == '__main__':
    unittest.main()

