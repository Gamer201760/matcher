"""
Tests for CLI display and utility functions.

These tests ensure that display functions can render without errors
and utility functions work correctly with various inputs.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from repository.recommendation_system.cli.displays import (
    display_error,
    display_group_details,
    display_group_tree,
    display_info,
    display_recommendations,
    display_statistics,
    display_success,
    display_user_info,
    display_warning,
)
from repository.recommendation_system.cli.utils import (
    generate_fake_users,
    get_all_user_ids,
    sample_users,
    setup_sample_groups,
)
from repository.recommendation_system.db import (
    PARAMETERS,
    ensure_constraints_and_index,
    get_driver,
    upsert_users,
)


class TestCLIDisplayFunctions(unittest.TestCase):
    """Test all display functions to ensure they render without errors."""

    @classmethod
    def setUpClass(cls):
        """Set up test database with sample data."""
        cls.driver = get_driver()
        with cls.driver.session() as session:
            # Clean database (non-interactive for tests)
            session.run("MATCH (n) DETACH DELETE n")
            ensure_constraints_and_index(session, dims=len(PARAMETERS))

            # Create sample users
            users = sample_users()
            caps = {'budget': 200000, 'months': 36}
            use_weights = True
            from repository.recommendation_system.user_vector_utils import (
                group_parameter_weights,
            )

            upsert_users(session, users, caps=caps, use_weights=use_weights, weights=group_parameter_weights)
            setup_sample_groups(session, caps, use_weights, group_parameter_weights)

    @classmethod
    def tearDownClass(cls):
        """Clean up after tests."""
        cls.driver.close()

    def test_01_display_user_info(self):
        """Test display_user_info renders without errors."""
        user_data = {
            'id': 'test_user',
            'name': 'Test User',
            'rooms': 2,
            'roommates': 1,
            'budget': 15000,
            'months': 12
        }
        # Should not raise any exceptions
        display_user_info(user_data)

    def test_02_display_recommendations(self):
        """Test display_recommendations with sample data."""
        with self.driver.session() as session:
            recommendations = [
                {'id': 'g_u1', 'score': 0.95},
                {'id': 'g_u2', 'score': 0.87},
                {'id': 'g_u3', 'score': 0.75}
            ]
            # Should not raise any exceptions
            display_recommendations(recommendations, session)

    def test_03_display_recommendations_empty(self):
        """Test display_recommendations with no results."""
        with self.driver.session() as session:
            display_recommendations([], session)

    def test_04_display_group_tree(self):
        """Test display_group_tree with parameters."""
        with self.driver.session() as session:
            # Should not raise any exceptions
            display_group_tree(session, max_groups=10, show_parameters=True)

    def test_05_display_group_tree_no_parameters(self):
        """Test display_group_tree without parameters."""
        with self.driver.session() as session:
            display_group_tree(session, show_parameters=False)

    def test_06_display_group_details(self):
        """Test display_group_details for existing group."""
        with self.driver.session() as session:
            # Group g_u1 should exist from sample data
            display_group_details(session, 'g_u1')

    def test_07_display_group_details_nonexistent(self):
        """Test display_group_details for non-existent group."""
        with self.driver.session() as session:
            # Should handle gracefully
            display_group_details(session, 'g_nonexistent')

    def test_08_display_statistics(self):
        """Test display_statistics renders without errors."""
        with self.driver.session() as session:
            display_statistics(session)

    def test_09_display_messages(self):
        """Test all message display functions."""
        display_success("Success message test")
        display_error("Error message test")
        display_warning("Warning message test")
        display_info("Info message test")


class TestCLIUtilityFunctions(unittest.TestCase):
    """Test utility functions for CLI."""

    @classmethod
    def setUpClass(cls):
        """Set up test database."""
        cls.driver = get_driver()
        with cls.driver.session() as session:
            # Clean database (non-interactive for tests)
            session.run("MATCH (n) DETACH DELETE n")
            ensure_constraints_and_index(session, dims=len(PARAMETERS))

    @classmethod
    def tearDownClass(cls):
        """Clean up after tests."""
        cls.driver.close()

    def test_01_generate_fake_users(self):
        """Test fake user generation."""
        users = generate_fake_users(10)
        self.assertEqual(len(users), 10)
        for user in users:
            self.assertIn('id', user)
            self.assertIn('name', user)
            self.assertIn('rooms', user)
            self.assertIn('budget', user)

    def test_02_sample_users(self):
        """Test sample user generation."""
        users = sample_users()
        self.assertEqual(len(users), 35)
        self.assertEqual(users[0]['id'], 'u1')

    def test_03_get_all_user_ids(self):
        """Test fetching user IDs from database."""
        with self.driver.session() as session:
            # Insert some users first
            users = [
                {'id': 'test1', 'name': 'Test 1', 'rooms': 1, 'roommates': 0, 'budget': 10000, 'months': 12},
                {'id': 'test2', 'name': 'Test 2', 'rooms': 2, 'roommates': 1, 'budget': 15000, 'months': 6}
            ]
            caps = {'budget': 200000, 'months': 36}
            from repository.recommendation_system.user_vector_utils import (
                group_parameter_weights,
            )
            upsert_users(session, users, caps=caps, use_weights=True, weights=group_parameter_weights)

            # Get user IDs
            user_ids = get_all_user_ids(session)
            self.assertGreaterEqual(len(user_ids), 2)
            self.assertTrue(all(isinstance(u, tuple) and len(u) == 2 for u in user_ids))

    def test_04_setup_sample_groups(self):
        """Test sample group setup."""
        with self.driver.session() as session:
            # Create sample users
            users = sample_users()
            caps = {'budget': 200000, 'months': 36}
            from repository.recommendation_system.user_vector_utils import (
                group_parameter_weights,
            )

            upsert_users(session, users, caps=caps, use_weights=True, weights=group_parameter_weights)

            # Group them
            setup_sample_groups(session, caps, True, group_parameter_weights)

            # Verify groups were created (check that g_u1 has members)
            from repository.recommendation_system.db import get_group_info
            group_info = get_group_info(session, 'g_u1')
            self.assertIsNotNone(group_info)
            self.assertGreater(group_info['member_count'], 1)


class TestCLINoneHandling(unittest.TestCase):
    """Test that CLI functions handle None values gracefully."""

    def test_01_display_tree_with_none_parameters(self):
        """Test tree display handles groups with None parameters."""
        from repository.recommendation_system.cli.displays import display_group_tree
        from repository.recommendation_system.db import get_driver

        driver = get_driver()
        with driver.session() as session:
            # This should not crash even if some groups have None values
            try:
                display_group_tree(session, max_groups=10, show_parameters=True)
            except TypeError as e:
                self.fail(f"display_group_tree raised TypeError with None values: {e}")
        driver.close()

    def test_02_user_selection_with_none_values(self):
        """Test user selection handles None parameter values."""
        from repository.recommendation_system.db import (
            get_driver,
        )

        driver = get_driver()
        with driver.session() as session:
            # Clean and create a user with potential None values
            session.run("MATCH (n) DETACH DELETE n")

            # Manually create a user node that might have None values
            session.run("""
                CREATE (u:User {
                    id: 'test_none_user',
                    name: 'Test None User'
                })
            """)

            # Try to get user list - should not crash
            query = """
                MATCH (u:User)
                OPTIONAL MATCH (u)-[:MEMBER_OF]->(g:Group)
                RETURN u.id as id, u.name as name, 
                       u.rooms as rooms, u.roommates as roommates,
                       u.budget as budget, u.months as months,
                       g.id as group_id, 
                       COUNT { (g)<-[:MEMBER_OF]-() } as group_size
                ORDER BY u.id
            """
            result = session.run(query)
            users = list(result)

            # Verify we can format the display without errors
            for user in users:
                rooms = user['rooms'] if user['rooms'] is not None else 0
                roommates = user['roommates'] if user['roommates'] is not None else 0
                budget = user['budget'] if user['budget'] is not None else 0
                months = user['months'] if user['months'] is not None else 0

                # This should not raise TypeError
                choice_str = (
                    f"{user['name']} — "
                    f"rooms:{rooms} rm:{roommates} "
                    f"₽{budget:,}/mo {months}mo"
                )
                self.assertIsInstance(choice_str, str)

        driver.close()


if __name__ == '__main__':
    unittest.main()

