"""
Menu system for interactive CLI.

Contains the main menu loop and startup configuration menu.
"""

from typing import Optional
from uuid import UUID

import questionary

from infrastructure.cli.actions import (
    action_clean_database,
    action_create_fake_users,
    action_create_new_user_main,
    action_delete_my_account,
    action_delete_my_group,
    action_get_recommendations,
    action_join_group,
    action_leave_group,
    action_switch_user,
    action_view_all_groups,
    action_view_my_group,
    action_view_statistics,
)
from infrastructure.cli.displays import (
    console,
    display_error,
    display_info,
)
from infrastructure.cli.utils import (
    auto_group_users,
    generate_fake_users,
    repair_users_without_groups,
    sample_users,
    setup_sample_groups,
)
from infrastructure.neo4j import clean_db, upsert_users
from infrastructure.neo4j.group_ops import get_group_by_user_id
from usecase.form import FormService
from usecase.group import FindGroupService, GroupService
from usecase.group_query import GroupQuery


def main_menu(
    session, current_user_id: UUID, caps: dict, use_weights: bool, weights: dict,
    form_service: FormService, group_service: GroupService,
    find_group_service: FindGroupService, group_query: GroupQuery
) -> UUID:
    """
    Main menu loop - runs until user exits.

    Args:
        session: Neo4j session
        current_user_id: Current user ID (UUID)
        caps: Normalization caps
        use_weights: Whether to use weighted vectors
        weights: Parameter weights
        form_service: FormService usecase
        group_service: GroupService usecase
        find_group_service: FindGroupService usecase
        group_query: GroupQuery usecase

    Returns:
        UUID: Current user ID (may have changed via switch user)
    """
    while True:
        # Show current user context with name
        user_query = 'MATCH (u:User {id: $user_id}) RETURN u.name as name'
        result = session.run(user_query, user_id=str(current_user_id))
        user_record = result.single()
        user_name = user_record['name'] if user_record else 'Unknown'

        console.print(
            f'\n[bold cyan]Current User:[/bold cyan] [yellow]{user_name}[/yellow] [dim]({current_user_id})[/dim]'
        )

        # Check if user is in a group

        current_group = get_group_by_user_id(session, str(current_user_id))
        is_in_multi_person_group = (
            current_group is not None and current_group.get('member_count', 0) > 1
        )

        # Build menu choices dynamically
        choices = [
            '🔍 Get Recommendations',
        ]

        # Only show Join if NOT in a multi-person group (single-person groups can still join)
        if not is_in_multi_person_group:
            choices.append('🤝 Join a Group')

        choices.extend(
            [
                '🚪 Leave My Group',
                '💥 Dissolve My Group',
                '👁️  View My Group',
                '🌳 View All Groups (Tree)',
                '👤 Switch User',
                '➕ Create New User',
                '🗑️  Delete My Account',
                '📊 View Statistics',
                '➕ Add Fake Users',
                '🔧 Repair Database',
                '🧹 Clean Database',
                '❌ Exit',
            ]
        )

        choice = questionary.select(
            '🏠 Roommate Matcher - Main Menu', choices=choices
        ).ask()

        if not choice:
            continue

        if choice == '🔍 Get Recommendations':
            action_get_recommendations(
                session, current_user_id, caps, use_weights, weights, find_group_service
            )

        elif choice == '🤝 Join a Group':
            action_join_group(session, current_user_id, caps, use_weights, weights,
                             find_group_service, group_service)

        elif choice == '🚪 Leave My Group':
            action_leave_group(session, current_user_id, caps, use_weights, weights,
                             form_service, group_query)

        elif choice == '💥 Dissolve My Group':
            action_delete_my_group(session, current_user_id, caps, use_weights, weights,
                                  group_query)

        elif choice == '👁️  View My Group':
            action_view_my_group(session, current_user_id, group_query)

        elif choice == '🌳 View All Groups (Tree)':
            action_view_all_groups(session, show_parameters=True)

        elif choice == '👤 Switch User':
            new_user_id = action_switch_user(session)
            if new_user_id:
                current_user_id = new_user_id

        elif choice == '➕ Create New User':
            new_user_id = action_create_new_user_main(
                session, caps, use_weights, weights
            )
            if new_user_id:
                display_info(f'Would you like to switch to the new user {new_user_id}?')
                switch = questionary.confirm('Switch to new user?', default=True).ask()
                if switch:
                    current_user_id = new_user_id

        elif choice == '🗑️  Delete My Account':
            new_user_id = action_delete_my_account(
                session, current_user_id, caps, use_weights, weights, form_service
            )
            if new_user_id:
                current_user_id = new_user_id
            else:
                # User cancelled or no users available, exit the menu
                console.print('\n[yellow]No user selected. Exiting...[/yellow]\n')
                break

        elif choice == '📊 View Statistics':
            action_view_statistics(session)

        elif choice == '➕ Add Fake Users':
            action_create_fake_users(session, caps, use_weights, weights)

        elif choice == '🔧 Repair Database':
            display_info('Checking for users without groups...')
            repaired = repair_users_without_groups(session, caps, use_weights, weights)
            if repaired > 0:
                console.print(f'[green]✓ Repaired {repaired} user(s) without groups[/green]')
            else:
                console.print('[green]✓ No issues found - all users have groups[/green]')

        elif choice == '🧹 Clean Database':
            action_clean_database(session)

        elif choice == '❌ Exit':
            console.print('\n[green]👋 Thanks for using Roommate Matcher![/green]\n')
            break

    return current_user_id


def select_user_with_details(
    session, caps: dict, use_weights: bool, weights: dict
) -> Optional[UUID]:
    """Select user showing their parameters and group status. Returns UUID or None."""
    # Get users with full details from Parameter nodes
    query = """
        MATCH (u:User)
        OPTIONAL MATCH (u)-[:MEMBER_OF]->(g:Group)
        OPTIONAL MATCH (u)-[:HAS_PARAMETER]->(p:Parameter)
        WITH u, g,
             collect({name: p.name, value: p.value}) as params
        RETURN u.id as id, u.name as name, 
               [param IN params WHERE param.name = 'rooms'][0].value as rooms,
               [param IN params WHERE param.name = 'roommates'][0].value as roommates,
               [param IN params WHERE param.name = 'budget'][0].value as budget,
               [param IN params WHERE param.name = 'months'][0].value as months,
               g.id as group_id, 
               COUNT { (g)<-[:MEMBER_OF]-() } as group_size
        ORDER BY u.id
    """
    result = session.run(query)
    users = list(result)

    if not users:
        display_error('No users found. Please restart and create users.')
        return None

    # Format choices with parameters
    choices = []

    # Add "Create New User" option at the TOP for visibility
    choices.append('➕ Create New User')

    for user in users:
        group_info = ''
        if user['group_id']:
            if user['group_size'] == 1:
                group_info = '[yellow]single-person group[/yellow]'
            else:
                group_info = f"[green]in group ({user['group_size']} members)[/green]"
        else:
            group_info = '[cyan]no group[/cyan]'

        # Handle None values with defaults
        rooms = user['rooms'] if user['rooms'] is not None else 0
        roommates = user['roommates'] if user['roommates'] is not None else 0
        budget = user['budget'] if user['budget'] is not None else 0
        months = user['months'] if user['months'] is not None else 0

        choice_str = (
            f"{user['name']} — "
            f"rooms:{rooms} rm:{roommates} "
            f"₽{budget:,}/mo {months}mo — "
            f"{group_info}"
        )
        choices.append(choice_str)

    choice = questionary.select(
        'Select your user (or create a new one):', choices=choices
    ).ask()

    if not choice:
        return None

    if 'Create New User' in choice:
        return action_create_new_user_main(session, caps, use_weights, weights)

    # Extract user ID from choice (find matching user) and convert to UUID
    # Note: choices[0] is "Create New User", so user choices start at index 1
    for i, user in enumerate(users):
        if choices[i + 1] == choice:  # +1 because choices[0] is "Create New User"
            return UUID(user['id'])

    return None


def startup_menu(
    session, caps: dict, use_weights: bool, weights: dict,
    form_service: FormService, group_service: GroupService,
    find_group_service: FindGroupService, group_query: GroupQuery
) -> Optional[UUID]:
    """
    Improved startup flow.

    Args:
        session: Neo4j session
        caps: Normalization caps
        use_weights: Whether to use weighted vectors
        weights: Parameter weights
        form_service: FormService usecase
        group_service: GroupService usecase
        find_group_service: FindGroupService usecase
        group_query: GroupQuery usecase

    Returns:
        UUID: User ID to start with, or None
    """
    # Ask about database cleanup
    clean = questionary.confirm('Clean database before starting?', default=False).ask()

    if clean:
        clean_db(session)
        console.print('[green]✓ Database cleaned[/green]')

        # Auto-create sample users
        console.print('[cyan]Creating sample users...[/cyan]')
        users = sample_users()
        # Allow customizing count
        count_choice = questionary.text(
            f'How many sample users to create? (default: {len(users)})',
            default=str(len(users)),
            validate=lambda x: x.isdigit() and int(x) > 0,
        ).ask()

        if not count_choice:
            return None

        if int(count_choice) != len(users):
            users = generate_fake_users(int(count_choice))
        else:
            users = sample_users()

        upsert_users(
            session, users, caps=caps, use_weights=use_weights, weights=weights
        )

        # Group them if using sample users
        if len(users) == 35:
            setup_sample_groups(session, caps, use_weights, weights)
        else:
            # Group random users probabilistically
            auto_group_users(session, users, caps, use_weights, weights)

        console.print(f'[green]✓ Created {len(users)} users[/green]')
        
        # Update statistics after user generation
        from infrastructure.cli.actions import update_parameter_statistics_action
        update_parameter_statistics_action()

    # Repair any users without groups (safety check after creation)
    repaired = repair_users_without_groups(session, caps, use_weights, weights)
    if repaired > 0:
        console.print(f'[yellow]⚠️  Repaired {repaired} user(s) that were missing groups[/yellow]')

    # Show enhanced user selection with parameters
    return select_user_with_details(session, caps, use_weights, weights)
