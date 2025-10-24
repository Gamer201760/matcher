#!/usr/bin/env python3
"""
Test runner for the recommendation system

Run this script from the project root to execute all tests.
"""
import os
import sys

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tests.rec_system_test import run_tests

if __name__ == '__main__':
    print("Starting Recommendation System Test Suite...")
    print("=" * 60)
    result = run_tests()

    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)

