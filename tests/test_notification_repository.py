"""
Unit tests for NotificationRepository

Tests notification logging functionality.
"""

import io
import logging
import unittest
from uuid import uuid4

from repository.notification_repository import NotificationRepository


class TestNotificationRepository(unittest.TestCase):
    """Test suite for NotificationRepository."""

    def setUp(self):
        """Set up before each test."""
        # Create repository instance
        self.repo = NotificationRepository()

        # Capture log output
        self.log_capture = io.StringIO()
        self.handler = logging.StreamHandler(self.log_capture)
        self.handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(levelname)s | %(message)s')
        self.handler.setFormatter(formatter)

        # Get the notification logger and add handler
        self.logger = logging.getLogger("notification_service")
        self.logger.addHandler(self.handler)

    def tearDown(self):
        """Clean up after each test."""
        # Remove handler
        self.logger.removeHandler(self.handler)
        self.handler.close()

    def test_01_notify_owner_of_new_request(self):
        """Test notifying owner of new join request."""
        group_id = uuid4()
        user_id = uuid4()

        # Send notification
        self.repo.notify_owner_of_new_request(group_id, user_id)

        # Check log output
        log_output = self.log_capture.getvalue()
        self.assertIn("NOTIFICATION", log_output)
        self.assertIn(str(group_id), log_output)
        self.assertIn(str(user_id), log_output)
        self.assertIn("join request", log_output.lower())

        print(f"✓ Logged notification for new request to group {group_id}")

    def test_02_notify_user_of_acceptance(self):
        """Test notifying user of request acceptance."""
        user_id = uuid4()
        group_id = uuid4()

        # Send notification
        self.repo.notify_user_of_decision(user_id, group_id, accepted=True)

        # Check log output
        log_output = self.log_capture.getvalue()
        self.assertIn("NOTIFICATION", log_output)
        self.assertIn(str(user_id), log_output)
        self.assertIn(str(group_id), log_output)
        self.assertIn("ACCEPTED", log_output)

        print(f"✓ Logged acceptance notification for user {user_id}")

    def test_03_notify_user_of_rejection(self):
        """Test notifying user of request rejection."""
        user_id = uuid4()
        group_id = uuid4()

        # Send notification
        self.repo.notify_user_of_decision(user_id, group_id, accepted=False)

        # Check log output
        log_output = self.log_capture.getvalue()
        self.assertIn("NOTIFICATION", log_output)
        self.assertIn(str(user_id), log_output)
        self.assertIn(str(group_id), log_output)
        self.assertIn("REJECTED", log_output)

        print(f"✓ Logged rejection notification for user {user_id}")

    def test_04_multiple_notifications(self):
        """Test sending multiple notifications."""
        group_id = uuid4()
        user_ids = [uuid4() for _ in range(3)]

        # Send multiple notifications
        for user_id in user_ids:
            self.repo.notify_owner_of_new_request(group_id, user_id)

        # Check log output contains all notifications
        log_output = self.log_capture.getvalue()
        for user_id in user_ids:
            self.assertIn(str(user_id), log_output)

        # Count occurrences
        notification_count = log_output.count("NOTIFICATION")
        self.assertEqual(notification_count, 3)

        print(f"✓ Logged {len(user_ids)} notifications")

    def test_05_context_manager(self):
        """Test repository works as context manager."""
        group_id = uuid4()
        user_id = uuid4()

        with NotificationRepository() as repo:
            repo.notify_owner_of_new_request(group_id, user_id)

        # Verify notification was logged
        log_output = self.log_capture.getvalue()
        self.assertIn("NOTIFICATION", log_output)

        print("✓ Context manager works correctly")

    def test_06_no_errors_on_valid_uuids(self):
        """Test that valid UUIDs don't cause errors."""
        group_id = uuid4()
        user_id = uuid4()

        try:
            self.repo.notify_owner_of_new_request(group_id, user_id)
            self.repo.notify_user_of_decision(user_id, group_id, True)
            self.repo.notify_user_of_decision(user_id, group_id, False)
            success = True
        except Exception as e:
            success = False
            print(f"Unexpected error: {e}")

        self.assertTrue(success)
        print("✓ No errors with valid UUID inputs")


if __name__ == '__main__':
    unittest.main()

