# Recommendation System Tests

This directory contains unit tests for the RecommendationService.

## Prerequisites

1. **Neo4j Database**: Make sure Neo4j is running
   - Install Neo4j Desktop or use a Neo4j instance
   - Start your Neo4j database
   - Note your connection credentials

2. **Environment Variables**: Configure your `.env` file
   ```bash
   # From project root
   cp .env.example .env
   # Edit .env with your Neo4j credentials
   ```

3. **Python Dependencies**: Install required packages
   ```bash
   pip install neo4j python-dotenv
   ```

## Running Tests

### Option 1: Using the test runner script (recommended)
```bash
# From project root
python run_tests.py
```

### Option 2: Run directly
```bash
# From project root
python tests/rec_system_test.py
```

### Option 3: Using unittest discovery
```bash
# From project root
python -m unittest discover tests
```

## Test Coverage

The test suite includes:

### Form Management Tests (Tests 1-6)
- ✅ `test_01_create_form` - Creating new user forms
- ✅ `test_02_get_form` - Retrieving user forms
- ✅ `test_03_get_form_not_found` - Error handling for non-existent forms
- ✅ `test_04_update_form` - Updating existing forms
- ✅ `test_05_delete_form` - Deleting user forms
- ✅ `test_06_get_similar` - Finding similar users based on preferences

### Group Management Tests (Tests 7-11)
- ✅ `test_07_send_request_to_group` - Sending join requests
- ✅ `test_08_approve_request` - Approving join requests
- ✅ `test_09_approve_request_makes_group_inactive` - Group capacity handling
- ✅ `test_10_leave_from_group` - Leaving groups
- ✅ `test_11_get_group` - Retrieving group information

### Integration Tests (Test 12)
- ✅ `test_12_integration_full_workflow` - Complete end-to-end workflow

## Test Structure

Each test follows this pattern:
1. **Setup**: Database is cleared before each test
2. **Execute**: Test the specific functionality
3. **Assert**: Verify expected behavior
4. **Teardown**: Cleanup (automatic)

## Important Notes

⚠️ **Warning**: Tests will **clear your database** before each test!
- Only run tests on a development/test database
- Never run tests on production data

## Troubleshooting

### Connection Issues
If you see "NEO4J DATABASE CONNECTION FAILED":
1. Verify Neo4j is running
2. Check your `.env` file credentials
3. Ensure the Neo4j URI is correct (usually `bolt://localhost:7687`)

### Import Errors
If you see import errors:
1. Make sure you're running from the project root
2. Verify all dependencies are installed
3. Check that the directory structure is correct

### Test Failures
- Check the detailed logs for specific error messages
- Ensure your Neo4j version supports vector indexes
- Verify your database has enough memory allocated

