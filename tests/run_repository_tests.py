"""
Test runner for all repository tests.

Runs all repository test suites in order and provides a summary.
"""

import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import all test modules
from test_form_repository import TestFormRepository
from test_group_repository import TestGroupRepository
from test_group_request_repository import TestGroupRequestRepository
from test_group_recommendation_repository import TestGroupRecommendationRepository
from test_notification_repository import TestNotificationRepository


def run_repository_tests():
    """Run all repository tests."""
    print("=" * 60)
    print("🧪 Repository Test Suite")
    print("=" * 60)
    print()
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestFormRepository))
    suite.addTests(loader.loadTestsFromTestCase(TestGroupRepository))
    suite.addTests(loader.loadTestsFromTestCase(TestGroupRequestRepository))
    suite.addTests(loader.loadTestsFromTestCase(TestGroupRecommendationRepository))
    suite.addTests(loader.loadTestsFromTestCase(TestNotificationRepository))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print()
    print("=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("✅ ALL REPOSITORY TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED")
    
    print("=" * 60)
    
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(run_repository_tests())

