"""
Unit tests for FormRepository

Tests form CRUD operations with Neo4j database.
"""

import os
from uuid import uuid4

import pytest
from neo4j import Driver

from entity.form import Form
from entity.parameters import Parameters, Sex, UserType
from entity.point import Point
from infrastructure.neo4j import (
    check_neo4j_connection,
    clear_users,
    ensure_constraints_and_index,
    get_driver,
)
from repository.form_repository import FormRepository


@pytest.fixture(scope='session')
def neo4j_driver():
    """Session-scoped fixture for Neo4j driver."""
    # Check Neo4j connection

    # Get driver instance
    driver = get_driver(
        os.getenv('NEO4J_URI', ''),
        os.getenv('NEO4J_USERNAME', ''),
        os.getenv('NEO4J_PASSWORD', ''),
    )

    if not check_neo4j_connection(driver):
        raise RuntimeError('Neo4j database is not available')

    # Initialize database constraints and indexes
    with driver.session() as session:
        ensure_constraints_and_index(session, dims=4)

    yield driver

    # Cleanup: close driver after all tests
    driver.close()


@pytest.fixture(scope='function')
def clean_database(neo4j_driver):
    """Clear database before each test."""
    with neo4j_driver.session() as session:
        clear_users(session)
    yield


@pytest.fixture(scope='function')
def form_repo(neo4j_driver: Driver):
    """Fixture to create and cleanup FormRepository instance."""
    repo = FormRepository(neo4j_driver)
    yield repo
    repo.close()


@pytest.fixture
def test_form():
    """Helper fixture to create a test form."""

    def _create_form(user_id=None) -> Form:
        if user_id is None:
            user_id = uuid4()

        parameters = Parameters(
            name='Test User',
            surname='Test Surname',
            geo=Point(55.7558, 37.6173),  # Moscow
            photos=['photo1.jpg', 'photo2.jpg'],
            budget=50000,
            room_count=2,
            roommates_count=1,
            month=12,
            age=25,
            smoking=False,
            alko=False,
            pet=True,
            sex=Sex.MALE,
            user_type=UserType.STUDENT,
            description='Looking for a quiet roommate',
        )

        return Form(user_id=user_id, parameters=parameters)

    return _create_form


def test_create_form(form_repo, test_form):
    """Test creating a new form."""
    form = test_form()

    # Create form
    result_id = form_repo.create(form)

    # Verify result
    assert result_id == form.user_id

    # Verify form was created in database
    retrieved_form = form_repo.get_by_user_id(form.user_id)
    assert retrieved_form is not None
    assert retrieved_form.user_id == form.user_id
    assert retrieved_form.parameters.budget == form.parameters.budget
    assert retrieved_form.parameters.room_count == form.parameters.room_count
    assert retrieved_form.parameters.roommates_count == form.parameters.roommates_count

    print(f'✓ Created form for user {form.user_id}')


def test_get_by_user_id(form_repo, test_form):
    """Test retrieving a form by user ID."""
    # Create a form
    form = test_form()
    form_repo.create(form)

    # Retrieve the form
    retrieved = form_repo.get_by_user_id(form.user_id)

    # Verify
    assert retrieved is not None
    assert retrieved.user_id == form.user_id
    assert retrieved.parameters.name == form.parameters.name
    assert retrieved.parameters.budget == form.parameters.budget

    print(f'✓ Retrieved form for user {form.user_id}')


def test_get_nonexistent_form(form_repo):
    """Test retrieving a non-existent form returns None."""
    fake_id = uuid4()

    # Try to retrieve non-existent form
    result = form_repo.get_by_user_id(fake_id)

    # Verify None is returned
    assert result is None

    print(f'✓ Correctly returned None for non-existent user {fake_id}')


def test_update_parameters(form_repo, test_form):
    """Test updating form parameters."""
    # Create initial form
    form = test_form()
    form_repo.create(form)

    # Update parameters
    new_parameters = Parameters(
        name='Updated User',
        surname='Updated Surname',
        geo=Point(55.7558, 37.6173),
        photos=[],
        budget=75000,  # Changed
        room_count=3,  # Changed
        roommates_count=2,  # Changed
        month=18,
        age=26,
        smoking=False,
        alko=True,
        pet=False,
        sex=Sex.MALE,
        user_type=UserType.WORKER,
        description='Updated description',
    )

    form_repo.update_parameters_by_user_id(form.user_id, new_parameters)

    # Retrieve and verify
    updated = form_repo.get_by_user_id(form.user_id)
    assert updated.parameters.budget == 75000
    assert updated.parameters.room_count == 3
    assert updated.parameters.roommates_count == 2

    print(f'✓ Updated parameters for user {form.user_id}')


def test_update_nonexistent_form(form_repo):
    """Test updating a non-existent form raises error."""
    fake_id = uuid4()

    new_parameters = Parameters(
        name='Test',
        surname='Test',
        geo=Point(0.0, 0.0),
        photos=[],
        budget=50000,
        room_count=2,
        roommates_count=1,
        month=12,
        age=25,
        smoking=False,
        alko=False,
        pet=False,
        sex=Sex.MALE,
        user_type=UserType.STUDENT,
        description='',
    )

    # Should raise ValueError
    with pytest.raises(ValueError):
        form_repo.update_parameters_by_user_id(fake_id, new_parameters)

    print(f'✓ Correctly raised error for updating non-existent user {fake_id}')


def test_delete_form(form_repo, test_form):
    """Test deleting a form."""
    # Create form
    form = test_form()
    form_repo.create(form)

    # Verify it exists
    assert form_repo.get_by_user_id(form.user_id) is not None

    # Delete the form
    form_repo.delete_by_user_id(form.user_id)

    # Verify it's gone
    result = form_repo.get_by_user_id(form.user_id)
    assert result is None

    print(f'✓ Deleted form for user {form.user_id}')


def test_delete_nonexistent_form(form_repo):
    """Test deleting a non-existent form doesn't raise error."""
    fake_id = uuid4()

    # Should not raise error
    try:
        form_repo.delete_by_user_id(fake_id)
        success = True
    except Exception as e:
        success = False
        print(f'Unexpected error: {e}')

    assert success
    print(f'✓ Gracefully handled deletion of non-existent user {fake_id}')


def test_multiple_forms(form_repo, test_form):
    """Test creating and managing multiple forms."""
    forms = [test_form() for _ in range(3)]

    # Create all forms
    for form in forms:
        form_repo.create(form)

    # Verify all exist
    for form in forms:
        retrieved = form_repo.get_by_user_id(form.user_id)
        assert retrieved is not None
        assert retrieved.user_id == form.user_id

    print(f'✓ Created and verified {len(forms)} forms')
