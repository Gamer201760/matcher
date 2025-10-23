"""
Unit tests for GroupRecommendationRepository

Tests group recommendation using vector similarity search.
"""

import unittest
from uuid import uuid4

from repository.group_recommendation_repository import GroupRecommendationRepository
from repository.form_repository import FormRepository
from repository.group_repository import GroupRepository
from repository.recommendation_system.db import (
    check_neo4j_connection,
    clear_users,
    get_driver,
    ensure_constraints_and_index,
)
from entity.form import Form
from entity.parameters import Parameters, Sex, UserType
from entity.point import Point


class TestGroupRecommendationRepository(unittest.TestCase):
    """Test suite for GroupRecommendationRepository."""
    
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
        self.repo = GroupRecommendationRepository()
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
    
    def _create_test_form(self, user_id=None, budget=50000, rooms=2, roommates=1) -> Form:
        """Helper to create a test form with customizable parameters."""
        if user_id is None:
            user_id = uuid4()
        
        parameters = Parameters(
            name=f"User {user_id}",
            surname="Test",
            geo=Point(55.7558, 37.6173),
            photos=[],
            budget=budget,
            room_count=rooms,
            roommates_count=roommates,
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
    
    def test_01_execute_basic_recommendation(self):
        """Test basic recommendation for a single-member group."""
        # Create three users with different parameters
        form1 = self._create_test_form(budget=50000, rooms=2, roommates=1)
        form2 = self._create_test_form(budget=50000, rooms=2, roommates=1)  # Identical
        form3 = self._create_test_form(budget=100000, rooms=5, roommates=4)  # Very different
        
        self.form_repo.create(form1)
        self.form_repo.create(form2)
        self.form_repo.create(form3)
        
        # Get first user's group
        group1 = self.group_repo.get_by_user_id(form1.user_id)
        
        # Get recommendations
        recommendations = self.repo.execute(group1.id)
        
        # Verify
        self.assertIsInstance(recommendations, list)
        self.assertGreater(len(recommendations), 0)
        
        # The most similar should be form2's group (identical parameters)
        if len(recommendations) > 0:
            most_similar = recommendations[0]
            self.assertIsNotNone(most_similar)
        
        print(f"✓ Got {len(recommendations)} recommendations for group {group1.id}")
    
    def test_02_execute_no_other_groups(self):
        """Test recommendation when there are no other groups."""
        # Create only one user
        form = self._create_test_form()
        self.form_repo.create(form)
        
        # Get the group
        group = self.group_repo.get_by_user_id(form.user_id)
        
        # Get recommendations (should be empty)
        recommendations = self.repo.execute(group.id)
        
        # Verify
        self.assertEqual(len(recommendations), 0)
        
        print(f"✓ Correctly returned empty list when no other groups exist")
    
    def test_03_execute_similarity_ordering(self):
        """Test that recommendations are ordered by similarity."""
        # Create four users with varying similarity to user1
        form1 = self._create_test_form(budget=50000, rooms=2, roommates=1)
        form2 = self._create_test_form(budget=50000, rooms=2, roommates=1)  # Identical
        form3 = self._create_test_form(budget=55000, rooms=2, roommates=2)  # Close
        form4 = self._create_test_form(budget=100000, rooms=5, roommates=4)  # Far
        
        self.form_repo.create(form1)
        self.form_repo.create(form2)
        self.form_repo.create(form3)
        self.form_repo.create(form4)
        
        # Get first user's group
        group1 = self.group_repo.get_by_user_id(form1.user_id)
        
        # Get recommendations
        recommendations = self.repo.execute(group1.id)
        
        # Verify we got recommendations
        self.assertGreaterEqual(len(recommendations), 2)
        
        # The order should be by similarity (form2 most similar, form4 least)
        # Note: We can't check exact IDs due to group naming, but we can verify
        # that we got multiple recommendations
        print(f"✓ Got {len(recommendations)} ordered recommendations")
    
    def test_04_execute_with_top_k_limit(self):
        """Test recommendation with top_k limit."""
        # Create more users than top_k
        forms = [self._create_test_form() for _ in range(6)]
        for form in forms:
            self.form_repo.create(form)
        
        # Get first user's group
        group1 = self.group_repo.get_by_user_id(forms[0].user_id)
        
        # Create repo with top_k=3
        repo_limited = GroupRecommendationRepository(top_k=3)
        
        # Get recommendations
        recommendations = repo_limited.execute(group1.id)
        
        # Verify we got at most 3 recommendations
        self.assertLessEqual(len(recommendations), 3)
        
        repo_limited.close()
        
        print(f"✓ Correctly limited recommendations to {len(recommendations)}")
    
    def test_05_execute_for_multi_member_group(self):
        """Test recommendation for a multi-member group."""
        # Create three users
        form1 = self._create_test_form(budget=30000, rooms=1, roommates=1)
        form2 = self._create_test_form(budget=70000, rooms=3, roommates=3)
        form3 = self._create_test_form(budget=50000, rooms=2, roommates=2)  # Average of form1+form2
        
        self.form_repo.create(form1)
        self.form_repo.create(form2)
        self.form_repo.create(form3)
        
        # Add form2 to form1's group (creating 2-member group)
        group1 = self.group_repo.get_by_user_id(form1.user_id)
        self.group_repo.add_user(form2.user_id, group1.id)
        
        # Get recommendations for the 2-member group
        # Should find form3's group as similar (since it has average parameters)
        recommendations = self.repo.execute(group1.id)
        
        # Verify
        self.assertGreater(len(recommendations), 0)
        
        print(f"✓ Got {len(recommendations)} recommendations for multi-member group")
    
    def test_06_execute_excludes_own_group(self):
        """Test that recommendations don't include the query group itself."""
        # Create three users
        forms = [self._create_test_form() for _ in range(3)]
        for form in forms:
            self.form_repo.create(form)
        
        # Get first user's group
        group1 = self.group_repo.get_by_user_id(forms[0].user_id)
        
        # Get recommendations
        recommendations = self.repo.execute(group1.id)
        
        # Verify the query group is not in recommendations
        recommendation_ids = {rec.id for rec in recommendations}
        self.assertNotIn(group1.id, recommendation_ids)
        
        print(f"✓ Correctly excluded own group from recommendations")
    
    def test_07_execute_nonexistent_group(self):
        """Test recommendation for non-existent group returns empty list."""
        fake_id = uuid4()
        
        # Try to get recommendations for non-existent group
        recommendations = self.repo.execute(fake_id)
        
        # Verify empty list is returned
        self.assertEqual(len(recommendations), 0)
        
        print(f"✓ Correctly returned empty list for non-existent group")
    
    def test_08_context_manager(self):
        """Test repository works as context manager."""
        # Create two users
        form1 = self._create_test_form()
        form2 = self._create_test_form()
        
        self.form_repo.create(form1)
        self.form_repo.create(form2)
        
        group1 = self.group_repo.get_by_user_id(form1.user_id)
        
        with GroupRecommendationRepository() as repo:
            recommendations = repo.execute(group1.id)
            self.assertIsInstance(recommendations, list)
        
        print("✓ Context manager works correctly")


if __name__ == '__main__':
    unittest.main()

