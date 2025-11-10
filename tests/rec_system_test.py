"""
Unit tests for RecommendationService

This test suite ensures all form management and group management
methods work correctly with the Neo4j database.
"""

import os
import sys
import unittest
import uuid

# Add parent directory to path to import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), '..', 'repository', 'recommendation_system'
        )
    ),
)

from entity.form import Form
from infrastructure.logging_utils import setup_logger
from infrastructure.neo4j import (
    PARAMETERS,
    check_neo4j_connection,
    clear_users,
    ensure_constraints_and_index,
    get_driver,
)

# Setup logger
logger = setup_logger('test_service', 'INFO')

# Helper function to generate UUIDs for testing
def test_uuid(name: str) -> str:
    """Generate UUID for testing"""
    return str(uuid.uuid4())


class TestRecommendationService(unittest.TestCase):
    """Test suite for RecommendationService"""

    @classmethod
    def setUpClass(cls):
        """Set up test environment once before all tests"""
        logger.info('=' * 60)
        logger.info('🧪 RecommendationService Unit Test Suite')
        logger.info('=' * 60)

        # Check Neo4j connection
        logger.info('🔍 Checking Neo4j database connection...')
        if not check_neo4j_connection():
            logger.error('❌ NEO4J DATABASE CONNECTION FAILED')
            logger.error('Make sure Neo4j is running and .env is configured correctly')
            raise RuntimeError('Neo4j connection failed. Cannot run tests.')

        logger.info('✅ Neo4j connection verified')

        # Initialize service
        cls.service = RecommendationService(use_weights=True)
        logger.info('✅ RecommendationService initialized')

    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests"""
        logger.info('\n🧹 Cleaning up test environment...')
        if hasattr(cls, 'service') and cls.service:
            cls.service.close()
        logger.info('✅ Test suite completed')
        logger.info('=' * 60)

    def setUp(self):
        """Set up before each test - clear database"""
        logger.info(f'\n📝 Running test: {self._testMethodName}')
        with get_driver() as driver:
            with driver.session() as session:
                ensure_constraints_and_index(session, dims=len(PARAMETERS))
                clear_users(session)
        logger.debug('Database cleared for test')

    def tearDown(self):
        """Clean up after each test"""
        logger.debug(f'Test {self._testMethodName} completed')

    # Form Management Tests

    def test_01_create_form(self):
        """Test creating a new user form"""
        logger.info('Testing create_form()...')

        user_id = test_uuid('test_user_1')
        form = Form(
            user_id=user_id,
            name='Test User 1',
            rooms=2,
            roommates=1,
            budget=15000,
            months=12,
        )

        # Create form
        self.service.create_form(user_id, form)
        logger.info(f'✓ Created form for user {user_id}')

        # Verify it was created
        retrieved_form = self.service.get_form(user_id)
        self.assertEqual(retrieved_form.user_id, user_id)
        self.assertEqual(retrieved_form.name, 'Test User 1')
        self.assertEqual(retrieved_form.rooms, 2)
        self.assertEqual(retrieved_form.roommates, 1)
        self.assertEqual(retrieved_form.budget, 15000)
        self.assertEqual(retrieved_form.months, 12)

        logger.info('✅ create_form test passed')

    def test_02_get_form(self):
        """Test retrieving a user form"""
        logger.info('Testing get_form()...')

        # Create a form first
        user_id = test_uuid('test_user_2')
        form = Form(
            user_id=user_id,
            name='Test User 2',
            rooms=1,
            roommates=2,
            budget=10000,
            months=6,
        )
        self.service.create_form(user_id, form)

        # Retrieve the form
        retrieved_form = self.service.get_form(user_id)

        self.assertIsNotNone(retrieved_form)
        self.assertEqual(retrieved_form.user_id, user_id)
        self.assertEqual(retrieved_form.name, 'Test User 2')
        self.assertEqual(retrieved_form.rooms, 1)
        self.assertEqual(retrieved_form.roommates, 2)
        self.assertEqual(retrieved_form.budget, 10000)
        self.assertEqual(retrieved_form.months, 6)

        logger.info('✅ get_form test passed')

    def test_03_get_form_not_found(self):
        """Test retrieving a non-existent form"""
        logger.info('Testing get_form() with non-existent user...')

        with self.assertRaises(ValueError) as context:
            self.service.get_form('non_existent_user')

        self.assertIn('not found', str(context.exception))
        logger.info('✅ get_form error handling test passed')

    def test_04_update_form(self):
        """Test updating an existing form"""
        logger.info('Testing update_form()...')

        # Create initial form
        user_id = test_uuid('test_user_3')
        form = Form(
            user_id=user_id,
            name='Test User 3',
            rooms=1,
            roommates=1,
            budget=10000,
            months=6,
        )
        self.service.create_form(user_id, form)
        logger.info('✓ Created initial form')

        # Update the form
        updated_form = Form(
            user_id=user_id,
            name='Test User 3 Updated',
            rooms=3,
            roommates=2,
            budget=20000,
            months=12,
        )
        self.service.update_form(user_id, updated_form)
        logger.info('✓ Updated form')

        # Verify updates
        retrieved_form = self.service.get_form(user_id)
        self.assertEqual(retrieved_form.name, 'Test User 3 Updated')
        self.assertEqual(retrieved_form.rooms, 3)
        self.assertEqual(retrieved_form.roommates, 2)
        self.assertEqual(retrieved_form.budget, 20000)
        self.assertEqual(retrieved_form.months, 12)

        logger.info('✅ update_form test passed')

    def test_05_delete_form(self):
        """Test deleting a user form"""
        logger.info('Testing delete_form()...')

        # Create a form
        user_id = test_uuid('test_user_4')
        form = Form(
            user_id=user_id,
            name='Test User 4',
            rooms=2,
            roommates=1,
            budget=15000,
            months=9,
        )
        self.service.create_form(user_id, form)
        logger.info('✓ Created form')

        # Verify it exists
        retrieved_form = self.service.get_form(user_id)
        self.assertIsNotNone(retrieved_form)

        # Delete the form
        self.service.delete_form(user_id)
        logger.info('✓ Deleted form')

        # Verify it's gone
        with self.assertRaises(ValueError):
            self.service.get_form(user_id)

        logger.info('✅ delete_form test passed')

    def test_06_get_similar(self):
        """Test finding similar users"""
        logger.info('Testing get_similar()...')

        # Create multiple users with varying preferences
        users = [
            Form(
                user_id=test_uuid('sim_user_1'),
                name='User 1',
                rooms=2,
                roommates=1,
                budget=15000,
                months=12,
            ),
            Form(
                user_id=test_uuid('sim_user_2'),
                name='User 2',
                rooms=2,
                roommates=1,
                budget=16000,
                months=12,
            ),
            Form(
                user_id=test_uuid('sim_user_3'),
                name='User 3',
                rooms=1,
                roommates=0,
                budget=8000,
                months=6,
            ),
            Form(
                user_id=test_uuid('sim_user_4'),
                name='User 4',
                rooms=3,
                roommates=3,
                budget=30000,
                months=18,
            ),
            Form(
                user_id=test_uuid('sim_user_5'),
                name='User 5',
                rooms=2,
                roommates=2,
                budget=14000,
                months=9,
            ),
        ]

        for form in users:
            self.service.create_form(form.user_id, form)
        logger.info(f'✓ Created {len(users)} test users')

        # Find similar users for sim_user_1
        similar = self.service.get_similar(test_uuid('sim_user_1'), top_k=3)

        self.assertIsNotNone(similar)
        self.assertGreater(len(similar), 0)
        self.assertLessEqual(len(similar), 3)

        # Check that results are tuples of (Form, score)
        for form, score in similar:
            self.assertIsInstance(form, Form)
            self.assertIsInstance(score, float)
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)
            self.assertNotEqual(
                form.user_id, test_uuid('sim_user_1')
            )  # Should not include query user

        # Most similar should be sim_user_2 (very similar preferences)
        most_similar_id = similar[0][0].user_id
        logger.info(
            f'✓ Most similar to sim_user_1: {most_similar_id} (score: {similar[0][1]:.4f})'
        )

        # Log all results
        for i, (form, score) in enumerate(similar, 1):
            logger.info(
                f'   {i}. {form.name} (ID: {form.user_id}) - {score*100:.1f}% match'
            )

        logger.info('✅ get_similar test passed')

    # Group Management Tests

    def test_07_send_request_to_group(self):
        """Test sending a join request to a group"""
        logger.info('Testing send_request_to_group()...')

        # Create two users
        user1_form = Form(
            user_id=test_uuid('group_user_1'),
            name='Group User 1',
            rooms=2,
            roommates=1,
            budget=15000,
            months=12,
        )
        user2_form = Form(
            user_id=test_uuid('group_user_2'),
            name='Group User 2',
            rooms=2,
            roommates=1,
            budget=16000,
            months=12,
        )

        self.service.create_form(test_uuid('group_user_1'), user1_form)
        self.service.create_form(test_uuid('group_user_2'), user2_form)
        logger.info('✓ Created 2 users')

        # User 2 sends request to User 1's group
        group_id = test_uuid('group_user_1')
        self.service.send_request_to_group(test_uuid('group_user_2'), group_id)
        logger.info(f'✓ User group_user_2 sent request to group {group_id}')

        # Verify request exists in database
        with get_driver() as driver:
            with driver.session() as session:
                check_query = """
                    MATCH (u:User {id: $user_id})-[r:JOIN_REQUEST]->(g:Group {id: $group_id})
                    RETURN r
                """
                result = session.run(
                    check_query, user_id=test_uuid('group_user_2'), group_id=group_id
                )
                self.assertIsNotNone(result.single())

        logger.info('✅ send_request_to_group test passed')

    def test_08_approve_request(self):
        """Test approving a join request"""
        logger.info('Testing approve_request()...')

        # Create two users
        user1_form = Form(
            user_id=test_uuid('approve_user_1'),
            name='Approve User 1',
            rooms=2,
            roommates=2,
            budget=15000,
            months=12,
        )
        user2_form = Form(
            user_id=test_uuid('approve_user_2'),
            name='Approve User 2',
            rooms=2,
            roommates=2,
            budget=16000,
            months=12,
        )

        self.service.create_form(test_uuid('approve_user_1'), user1_form)
        self.service.create_form(test_uuid('approve_user_2'), user2_form)
        logger.info('✓ Created 2 users')

        # User 2 sends request to User 1's group
        group_id = test_uuid('approve_user_1')
        self.service.send_request_to_group(test_uuid('approve_user_2'), group_id)
        logger.info('✓ Request sent')

        # User 1 approves the request
        self.service.approve_request(
            test_uuid('approve_user_1'), test_uuid('approve_user_2'), max_roommates=4
        )
        logger.info('✓ Request approved')

        # Verify User 2 is now in User 1's group
        with get_driver() as driver:
            with driver.session() as session:
                check_query = """
                    MATCH (u:User {id: $user_id})-[:MEMBER_OF]->(g:Group {id: $group_id})
                    RETURN g.id as group_id
                """
                result = session.run(
                    check_query, user_id=test_uuid('approve_user_2'), group_id=group_id
                )
                record = result.single()
                self.assertIsNotNone(record)
                self.assertEqual(record['group_id'], group_id)

        logger.info('✅ approve_request test passed')

    def test_09_approve_request_makes_group_inactive(self):
        """Test that approving requests makes group inactive when full"""
        logger.info('Testing approve_request() with max capacity...')

        # Create users
        users = []
        for i in range(1, 5):  # 4 users
            form = Form(
                user_id=test_uuid(f'capacity_user_{i}'),
                name=f'Capacity User {i}',
                rooms=2,
                roommates=4,
                budget=15000,
                months=12,
            )
            self.service.create_form(test_uuid(f'capacity_user_{i}'), form)
            users.append(test_uuid(f'capacity_user_{i}'))

        logger.info(f'✓ Created {len(users)} users')

        # Users 2, 3, 4 send requests to User 1's group
        group_id = test_uuid('capacity_user_1')
        for i in range(2, 5):
            self.service.send_request_to_group(test_uuid(f'capacity_user_{i}'), group_id)
        logger.info('✓ Requests sent')

        # User 1 approves requests (max_roommates = 4)
        for i in range(2, 5):
            self.service.approve_request(
                test_uuid('capacity_user_1'), test_uuid(f'capacity_user_{i}'), max_roommates=4
            )
            logger.info(f'✓ Approved capacity_user_{i}')

        # Check group is now inactive
        group, members = self.service.get_group(group_id)
        self.assertEqual(len(members), 4)
        self.assertFalse(group.active)

        logger.info(f'✓ Group {group_id} is now inactive with {len(members)} members')
        logger.info('✅ approve_request capacity test passed')

    def test_10_leave_from_group(self):
        """Test leaving from a group"""
        logger.info('Testing leave_from_group()...')

        # Create three users and form a group
        for i in range(1, 4):
            form = Form(
                user_id=test_uuid(f'leave_user_{i}'),
                name=f'Leave User {i}',
                rooms=2,
                roommates=2,
                budget=15000,
                months=12,
            )
            self.service.create_form(test_uuid(f'leave_user_{i}'), form)
        logger.info('✓ Created 3 users')

        # Users 2 and 3 join User 1's group
        group_id = test_uuid('leave_user_1')
        for i in range(2, 4):
            self.service.send_request_to_group(test_uuid(f'leave_user_{i}'), group_id)
            self.service.approve_request(
                test_uuid('leave_user_1'), test_uuid(f'leave_user_{i}'), max_roommates=5
            )
        logger.info('✓ Formed group with 3 members')

        # Verify group has 3 members
        group, members = self.service.get_group(group_id)
        self.assertEqual(len(members), 3)

        # User 2 leaves the group
        self.service.leave_from_group(test_uuid('leave_user_2'))
        logger.info('✓ leave_user_2 left the group')

        # Verify User 2 is now in their own group
        with get_driver() as driver:
            with driver.session() as session:
                check_query = """
                    MATCH (u:User {id: $user_id})-[:MEMBER_OF]->(g:Group)
                    RETURN g.id as group_id
                """
                result = session.run(check_query, user_id=test_uuid('leave_user_2'))
                record = result.single()
                self.assertIsNotNone(record)
                self.assertEqual(record['group_id'], test_uuid('leave_user_2'))

        # Verify original group now has 2 members
        group, members = self.service.get_group(group_id)
        self.assertEqual(len(members), 2)

        logger.info('✅ leave_from_group test passed')

    def test_11_get_group(self):
        """Test getting group information"""
        logger.info('Testing get_group()...')

        # Create users
        for i in range(1, 4):
            form = Form(
                user_id=test_uuid(f'info_user_{i}'),
                name=f'Info User {i}',
                rooms=2,
                roommates=3,
                budget=15000,
                months=12,
            )
            self.service.create_form(test_uuid(f'info_user_{i}'), form)
        logger.info('✓ Created 3 users')

        # Form a group
        group_id = test_uuid('info_user_1')
        for i in range(2, 4):
            self.service.send_request_to_group(test_uuid(f'info_user_{i}'), group_id)
            self.service.approve_request(
                test_uuid('info_user_1'), test_uuid(f'info_user_{i}'), max_roommates=5
            )
        logger.info('✓ Formed group with 3 members')

        # Get group information
        group, members = self.service.get_group(group_id)

        # Verify group object
        self.assertIsInstance(group, Group)
        self.assertEqual(group.group_id, group_id)
        self.assertTrue(group.active)

        # Verify members
        self.assertEqual(len(members), 3)
        self.assertIn(test_uuid('info_user_1'), members)
        self.assertIn(test_uuid('info_user_2'), members)
        self.assertIn(test_uuid('info_user_3'), members)

        logger.info(
            f'✓ Group {group_id}: {len(members)} members, active={group.active}'
        )
        logger.info(f"   Members: {', '.join(members)}")
        logger.info('✅ get_group test passed')

    def test_12_integration_full_workflow(self):
        """Test complete workflow: create, match, form groups, leave"""
        logger.info('Testing full integration workflow...')

        # Step 1: Create multiple users
        users_data = [
            ('workflow_u1', 'Alice', 2, 1, 15000, 12),
            ('workflow_u2', 'Bob', 2, 1, 16000, 12),
            ('workflow_u3', 'Charlie', 2, 2, 14000, 9),
            ('workflow_u4', 'Dave', 1, 0, 8000, 6),
        ]

        for user_id, name, rooms, roommates, budget, months in users_data:
            form = Form(
                user_id=user_id,
                name=name,
                rooms=rooms,
                roommates=roommates,
                budget=budget,
                months=months,
            )
            self.service.create_form(user_id, form)

        logger.info(f'✓ Step 1: Created {len(users_data)} users')

        # Step 2: Find similar users for Alice
        similar = self.service.get_similar('workflow_u1', top_k=3)
        self.assertGreater(len(similar), 0)
        logger.info(f'✓ Step 2: Found {len(similar)} similar users for Alice')
        for form, score in similar:
            logger.info(f'   - {form.name}: {score*100:.1f}% match')

        # Step 3: Bob requests to join Alice's group
        alice_group = 'g_workflow_u1'
        self.service.send_request_to_group('workflow_u2', alice_group)
        logger.info("✓ Step 3: Bob sent request to Alice's group")

        # Step 4: Alice approves Bob
        self.service.approve_request('workflow_u1', 'workflow_u2', max_roommates=4)
        logger.info("✓ Step 4: Alice approved Bob's request")

        # Step 5: Verify group formation
        group, members = self.service.get_group(alice_group)
        self.assertEqual(len(members), 2)
        self.assertIn('workflow_u1', members)
        self.assertIn('workflow_u2', members)
        logger.info(f'✓ Step 5: Group formed with {len(members)} members')

        # Step 6: Bob leaves the group
        self.service.leave_from_group('workflow_u2')
        logger.info('✓ Step 6: Bob left the group')

        # Step 7: Verify Bob is in his own group again
        bob_group, bob_members = self.service.get_group('g_workflow_u2')
        self.assertEqual(len(bob_members), 1)
        self.assertIn('workflow_u2', bob_members)
        logger.info('✓ Step 7: Bob is now in his own group')

        # Step 8: Verify Alice's group is back to 1 member
        alice_group_after, alice_members = self.service.get_group(alice_group)
        self.assertEqual(len(alice_members), 1)
        logger.info("✓ Step 8: Alice's group back to 1 member")

        logger.info('✅ Full integration workflow test passed')


def run_tests():
    """Run all tests"""
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestRecommendationService)

    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Summary
    logger.info('\n' + '=' * 60)
    logger.info('📊 TEST SUMMARY')
    logger.info('=' * 60)
    logger.info(f'Tests run: {result.testsRun}')
    logger.info(
        f'Successes: {result.testsRun - len(result.failures) - len(result.errors)}'
    )
    logger.info(f'Failures: {len(result.failures)}')
    logger.info(f'Errors: {len(result.errors)}')

    if result.wasSuccessful():
        logger.info('✅ ALL TESTS PASSED!')
    else:
        logger.error('❌ SOME TESTS FAILED')

    logger.info('=' * 60)

    return result


if __name__ == '__main__':
    run_tests()
