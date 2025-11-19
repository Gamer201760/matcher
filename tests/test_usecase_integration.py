"""
Integration tests for UseCase layer with add_user_to_group refactoring.

Tests that usecases (FormService, GroupService) properly orchestrate
the refactored infrastructure layer operations:
- add_user only creates relationships
- calculate_params is called separately by usecases
- Group deletion is handled by usecases
"""

import os
import pytest
from uuid import uuid4, UUID

from entity.form import Form
from entity.group import Group
from entity.parameters import Parameters, Sex, UserType
from entity.point import Point
from entity.group import GroupRequest
from infrastructure.neo4j import (
    check_neo4j_connection,
    clear_users,
    ensure_constraints_and_index,
    get_driver,
)
from repository.form_repository import FormRepository
from repository.group_repository import GroupRepository
from repository.group_request_repository import GroupRequestRepository
from usecase.form import FormService
from usecase.group import GroupService, FindGroupService
from repository.group_recommendation_repository import GroupRecommendationRepository


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(scope='session')
def neo4j_driver():
    """Session-scoped fixture for Neo4j driver."""
    driver = get_driver(
        os.getenv('NEO4J_URI', 'bolt://localhost:7687'),
        os.getenv('NEO4J_USERNAME', 'neo4j'),
        os.getenv('NEO4J_PASSWORD', '123456789'),
    )
    
    if not check_neo4j_connection(driver):
        raise RuntimeError('Neo4j database is not available')
    
    # Initialize database constraints and indexes
    with driver.session() as session:
        ensure_constraints_and_index(session, dims=4)
    
    yield driver
    
    driver.close()


@pytest.fixture(scope='function')
def clean_database(neo4j_driver):
    """Clear database before each test."""
    with neo4j_driver.session() as session:
        clear_users(session)
    yield


@pytest.fixture
def repositories(neo4j_driver):
    """Create repository instances."""
    form_repo = FormRepository(neo4j_driver)
    group_repo = GroupRepository(neo4j_driver)
    request_repo = GroupRequestRepository(neo4j_driver)
    recommendation_repo = GroupRecommendationRepository(neo4j_driver)
    
    return {
        'form': form_repo,
        'group': group_repo,
        'request': request_repo,
        'recommendation': recommendation_repo,
    }


@pytest.fixture
def services(repositories):
    """Create usecase service instances."""
    form_service = FormService(
        form_repo=repositories['form'],
        group_repo=repositories['group'],
    )
    
    group_service = GroupService(
        group_repo=repositories['group'],
        request_repo=repositories['request'],
    )
    
    find_group_service = FindGroupService(
        group_repo=repositories['group'],
        recommendation_repo=repositories['recommendation'],
    )
    
    return {
        'form': form_service,
        'group': group_service,
        'find_group': find_group_service,
    }


@pytest.fixture
def sample_parameters():
    """Factory for creating test parameters."""
    def _create(budget=50000, rooms=2, roommates=1, name='Test User'):
        return Parameters(
            name=name,
            surname='Test',
            geo=Point(55.7558, 37.6173),  # Moscow
            photos=[],
            budget=budget,
            room_count=rooms,
            roommates_count=roommates,
            month=12,
            age=25,
            smoking=False,
            alko=False,
            pet=False,
            sex=Sex.MALE,
            user_type=UserType.STUDENT,
            description='Test user',
        )
    return _create


# ============================================================================
# TEST: FormService.create uses add_user correctly
# ============================================================================

def test_form_service_create_uses_add_user(
    clean_database, services, repositories, sample_parameters
):
    """
    Test that FormService.create properly calls add_user and calculate_params.
    
    Flow:
    1. Create form (creates User)
    2. Create group (creates Group)
    3. Call add_user (creates MEMBER_OF relationship only)
    4. Call calculate_params (updates group parameters)
    """
    user_id = uuid4()
    params = sample_parameters(budget=40000, rooms=2, roommates=1, name='Alice')
    
    # Create form via UseCase
    services['form'].create(user_id, params)
    
    # Verify user exists
    form = repositories['form'].get_by_user_id(user_id)
    assert form is not None
    assert form.user_id == user_id
    assert form.parameters.budget == 40000
    
    # Verify group exists
    group = repositories['group'].get_by_owner_id(user_id)
    assert group is not None
    assert group.owner_id == user_id
    
    # Verify user is member of group
    members = repositories['group'].list_members(group.id)
    assert len(members) == 1
    assert members[0].user_id == user_id
    
    # Verify group parameters were calculated correctly
    assert group.parameters.budget == 40000
    assert group.parameters.room_count == 2
    
    print(f"✓ FormService.create correctly orchestrated add_user + calculate_params")


def test_form_service_create_multiple_users(
    clean_database, services, repositories, sample_parameters
):
    """Test creating multiple users each gets their own group."""
    users = [
        (uuid4(), sample_parameters(budget=30000, name='Alice')),
        (uuid4(), sample_parameters(budget=50000, name='Bob')),
        (uuid4(), sample_parameters(budget=70000, name='Charlie')),
    ]
    
    # Create all users
    for user_id, params in users:
        services['form'].create(user_id, params)
    
    # Verify each has their own group
    for user_id, params in users:
        group = repositories['group'].get_by_owner_id(user_id)
        assert group is not None
        assert group.owner_id == user_id
        
        members = repositories['group'].list_members(group.id)
        assert len(members) == 1
        assert members[0].user_id == user_id
    
    print(f"✓ Created {len(users)} users, each with their own group")


# ============================================================================
# TEST: GroupService.accept_join_request orchestration
# ============================================================================

def test_group_service_accept_request_orchestration(
    clean_database, services, repositories, sample_parameters, neo4j_driver
):
    """
    Test that GroupService.accept_join_request properly orchestrates:
    1. Delete old group
    2. Add user to new group (creates relationship only)
    3. Calculate group parameters (updates averaged parameters)
    """
    # Create two users with different parameters
    alice_id = uuid4()
    bob_id = uuid4()
    
    alice_params = sample_parameters(budget=40000, rooms=2, roommates=2, name='Alice')
    bob_params = sample_parameters(budget=60000, rooms=3, roommates=2, name='Bob')
    
    services['form'].create(alice_id, alice_params)
    services['form'].create(bob_id, bob_params)
    
    # Get Alice's group
    alice_group = repositories['group'].get_by_owner_id(alice_id)
    
    # Bob sends join request to Alice's group
    request_id = uuid4()
    with neo4j_driver.session() as session:
        from infrastructure.neo4j.request_ops import create_join_request_with_id
        create_join_request_with_id(
            session,
            str(request_id),
            str(bob_id),
            str(alice_group.id),
        )
    
    # Get Bob's group before accepting (should exist)
    bob_old_group = repositories['group'].get_by_owner_id(bob_id)
    assert bob_old_group is not None
    bob_old_group_id = bob_old_group.id
    
    # Alice accepts Bob's request
    services['group'].accept_join_request(alice_id, request_id)
    
    # Verify Bob's old group was deleted
    from entity.errors import NotFoundError
    with pytest.raises(NotFoundError):
        repositories['group'].get(bob_old_group_id)
    
    # Verify Bob is now member of Alice's group
    members = repositories['group'].list_members(alice_group.id)
    assert len(members) == 2
    member_ids = {m.user_id for m in members}
    assert alice_id in member_ids
    assert bob_id in member_ids
    
    # Verify group parameters were recalculated (averaged)
    updated_group = repositories['group'].get(alice_group.id)
    expected_budget = (40000 + 60000) / 2  # 50000
    expected_rooms = (2 + 3) / 2  # 2.5
    
    print(f"\n🔍 DEBUG: Group ID: {alice_group.id}")
    print(f"🔍 DEBUG: Actual budget: {updated_group.parameters.budget}, Expected: {expected_budget}")
    print(f"🔍 DEBUG: Actual rooms: {updated_group.parameters.room_count}, Expected: {expected_rooms}")
    print(f"🔍 DEBUG: Budget diff: {abs(updated_group.parameters.budget - expected_budget)}")
    print(f"🔍 DEBUG: Rooms diff: {abs(updated_group.parameters.room_count - expected_rooms)}")
    
    assert abs(updated_group.parameters.budget - expected_budget) < 1
    assert abs(updated_group.parameters.room_count - expected_rooms) < 0.1
    
    print(f"✓ GroupService.accept_join_request correctly orchestrated:")
    print(f"  - Deleted old group")
    print(f"  - Added user to new group")
    print(f"  - Recalculated group parameters (budget: {updated_group.parameters.budget}, rooms: {updated_group.parameters.room_count})")


def test_accept_request_three_users_sequential(
    clean_database, services, repositories, sample_parameters, neo4j_driver
):
    """Test accepting multiple join requests sequentially."""
    # Create three users
    alice_id = uuid4()
    bob_id = uuid4()
    charlie_id = uuid4()
    
    alice_params = sample_parameters(budget=30000, rooms=1, roommates=3, name='Alice')
    bob_params = sample_parameters(budget=60000, rooms=2, roommates=3, name='Bob')
    charlie_params = sample_parameters(budget=90000, rooms=3, roommates=3, name='Charlie')
    
    services['form'].create(alice_id, alice_params)
    services['form'].create(bob_id, bob_params)
    services['form'].create(charlie_id, charlie_params)
    
    alice_group = repositories['group'].get_by_owner_id(alice_id)
    
    # Bob joins Alice's group
    request1_id = uuid4()
    with neo4j_driver.session() as session:
        from infrastructure.neo4j.request_ops import create_join_request_with_id
        create_join_request_with_id(
            session, str(request1_id), str(bob_id), str(alice_group.id)
        )
    
    services['group'].accept_join_request(alice_id, request1_id)
    
    # Verify 2 members, averaged parameters
    members = repositories['group'].list_members(alice_group.id)
    assert len(members) == 2
    
    group = repositories['group'].get(alice_group.id)
    expected_budget_2 = (30000 + 60000) / 2  # 45000
    assert abs(group.parameters.budget - expected_budget_2) < 1
    
    # Charlie joins the group
    request2_id = uuid4()
    with neo4j_driver.session() as session:
        from infrastructure.neo4j.request_ops import create_join_request_with_id
        create_join_request_with_id(
            session, str(request2_id), str(charlie_id), str(alice_group.id)
        )
    
    services['group'].accept_join_request(alice_id, request2_id)
    
    # Verify 3 members, recalculated parameters
    members = repositories['group'].list_members(alice_group.id)
    assert len(members) == 3
    
    group = repositories['group'].get(alice_group.id)
    expected_budget_3 = (30000 + 60000 + 90000) / 3  # 60000
    expected_rooms_3 = (1 + 2 + 3) / 3  # 2.0
    
    assert abs(group.parameters.budget - expected_budget_3) < 1
    assert abs(group.parameters.room_count - expected_rooms_3) < 0.1
    
    print(f"✓ Sequential join requests handled correctly:")
    print(f"  - 3 members in group")
    print(f"  - Final budget: {group.parameters.budget} (expected: 60000)")
    print(f"  - Final rooms: {group.parameters.room_count} (expected: 2.0)")


# ============================================================================
# TEST: Verify add_user doesn't auto-update parameters
# ============================================================================

def test_add_user_does_not_auto_update_group_params(
    clean_database, repositories, sample_parameters, neo4j_driver
):
    """
    Test that add_user (infrastructure layer) only creates relationship,
    does NOT update group parameters automatically.
    """
    # Create two users manually
    alice_id = uuid4()
    bob_id = uuid4()
    
    from infrastructure.neo4j import upsert_users
    users = [
        {
            'id': str(alice_id),
            'name': 'Alice',
            'rooms': 2,
            'roommates': 1,
            'budget': 40000,
            'months': 12,
        },
        {
            'id': str(bob_id),
            'name': 'Bob',
            'rooms': 3,
            'roommates': 1,
            'budget': 60000,
            'months': 12,
        }
    ]
    
    with neo4j_driver.session() as session:
        upsert_users(session, users)
    
    # Create a group manually
    from infrastructure.neo4j.group_ops import create_empty_group
    from recommendation import create_vector
    from infrastructure.config import PARAMETERS, get_parameter_statistics
    
    group_id = str(uuid4())
    group_params = {'rooms': 2, 'roommates': 1, 'budget': 40000, 'months': 12}
    group_vector = create_vector(
        group_params, PARAMETERS, statistics=get_parameter_statistics()
    )
    
    with neo4j_driver.session() as session:
        create_empty_group(
            session, group_id, 'Test Group', str(alice_id), group_params, group_vector
        )
    
    # Add Alice to group
    from infrastructure.neo4j.group_ops import add_user_to_group, get_group_info
    
    with neo4j_driver.session() as session:
        add_user_to_group(session, str(alice_id), group_id)
        
        # Check group parameters (should still be original)
        group_info = get_group_info(session, group_id)
        assert group_info['parameters']['budget'] == 40000
        assert group_info['parameters']['rooms'] == 2
    
    # Add Bob to group
    with neo4j_driver.session() as session:
        add_user_to_group(session, str(bob_id), group_id)
        
        # Check group parameters (should STILL be original, not averaged)
        group_info = get_group_info(session, group_id)
        assert group_info['parameters']['budget'] == 40000  # NOT 50000
        assert group_info['parameters']['rooms'] == 2  # NOT 2.5
        assert group_info['member_count'] == 2
    
    print(f"✓ add_user_to_group does NOT auto-update group parameters")
    print(f"  - Budget stayed: {group_info['parameters']['budget']} (not averaged to 50000)")
    print(f"  - Rooms stayed: {group_info['parameters']['rooms']} (not averaged to 2.5)")


# ============================================================================
# TEST: Edge cases
# ============================================================================

def test_add_user_idempotency(
    clean_database, services, repositories, sample_parameters
):
    """Test that adding same user twice is idempotent."""
    user_id = uuid4()
    params = sample_parameters(name='Alice')
    
    services['form'].create(user_id, params)
    group = repositories['group'].get_by_owner_id(user_id)
    
    # Try adding user to their own group again
    repositories['group'].add_user(user_id, group.id)
    
    # Should still be only 1 member
    members = repositories['group'].list_members(group.id)
    assert len(members) == 1
    
    print("✓ add_user is idempotent")


def test_calculate_params_after_add_user(
    clean_database, repositories, sample_parameters, neo4j_driver
):
    """Test explicitly calling calculate_params after add_user."""
    # Create two users
    alice_id = uuid4()
    bob_id = uuid4()
    
    alice_params = sample_parameters(budget=40000, rooms=2, name='Alice')
    bob_params = sample_parameters(budget=60000, rooms=3, name='Bob')
    
    # Use FormService to create (includes group creation)
    from usecase.form import FormService
    form_service = FormService(repositories['form'], repositories['group'])
    
    form_service.create(alice_id, alice_params)
    form_service.create(bob_id, bob_params)
    
    alice_group = repositories['group'].get_by_owner_id(alice_id)
    
    # Manually add Bob to Alice's group (infrastructure layer)
    repositories['group'].add_user(bob_id, alice_group.id)
    
    # Parameters should NOT be updated yet
    group_before = repositories['group'].get(alice_group.id)
    assert group_before.parameters.budget == 40000  # Still Alice's original
    
    # Now explicitly calculate parameters
    repositories['group'].calculate_params(alice_group.id)
    
    # Parameters should NOW be averaged
    group_after = repositories['group'].get(alice_group.id)
    expected_budget = (40000 + 60000) / 2
    assert abs(group_after.parameters.budget - expected_budget) < 1
    
    print("✓ calculate_params correctly updates after add_user")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

