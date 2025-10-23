#!/usr/bin/env python3
"""
Simple test runner for repository tests.

Usage:
    python tests/run_tests.py                    # Run all tests
    python tests/run_tests.py form               # Run FormRepository tests
    python tests/run_tests.py group              # Run GroupRepository tests
    python tests/run_tests.py request            # Run GroupRequestRepository tests
    python tests/run_tests.py recommendation     # Run GroupRecommendationRepository tests
    python tests/run_tests.py notification       # Run NotificationRepository tests
"""

import sys
import subprocess
from pathlib import Path

# Test file mapping
TEST_FILES = {
    'form': 'tests/test_form_repository.py',
    'group': 'tests/test_group_repository.py',
    'request': 'tests/test_group_request_repository.py',
    'recommendation': 'tests/test_group_recommendation_repository.py',
    'notification': 'tests/test_notification_repository.py',
    'all': 'tests/test_*.py',
}

def main():
    if len(sys.argv) < 2:
        # Run all tests
        test_target = 'all'
    else:
        test_target = sys.argv[1].lower()
    
    if test_target not in TEST_FILES:
        print(f"Unknown test target: {test_target}")
        print(f"\nAvailable targets: {', '.join(TEST_FILES.keys())}")
        sys.exit(1)
    
    test_path = TEST_FILES[test_target]
    
    print(f"{'='*60}")
    print(f"Running {test_target} tests...")
    print(f"{'='*60}\n")
    
    # Run pytest with verbose output
    cmd = ['python', '-m', 'pytest', test_path, '-v', '--tb=short']
    
    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)
    sys.exit(result.returncode)

if __name__ == '__main__':
    main()

