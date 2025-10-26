"""
Action handlers for user interactions.

Contains all the flow logic for menu actions like joining groups,
getting recommendations, switching users, etc.
"""

from typing import Optional

import questionary
from rich.table import Table

from infrastructure.cli.displays import (
    console,
    display_error,
    display_group_details,
    display_group_tree,
    display_info,
    display_recommendations,
    display_statistics,
    display_success,
    display_warning,
)
from infrastructure.cli.utils import (
    create_user_interactive,
    generate_fake_users,
    get_all_user_ids,
    sample_users,
    setup_sample_groups,
)
from infrastructure.neo4j import (
    PARAMETERS,
    add_user_to_group,
    clean_db,
    find_similar,
    get_group_by_user_id,
    get_user_parameters,
    remove_user_from_group,
    upsert_users,
)
from infrastructure.neo4j.connection import ensure_constraints_and_index
from infrastructure.neo4j.group_ops import get_group_member_parameters
from infrastructure.user_vector_utils import (
    create_group_vector_with_weights,
    create_user_vector,
)


def action_get_recommendations(
    session, current_user_id: str, caps: dict, use_weights: bool, weights: dict
):
    """
    Flow: Get and display recommendations for current user with auto-retry on index errors.

    Args:
        session: Neo4j session
        current_user_id: Current user ID
        caps: Normalization caps
        use_weights: Whether to use weighted vectors
        weights: Parameter weights
    """
    try:
        # Get user data
        user_params = get_user_parameters(session, current_user_id)

        if not user_params:
            display_error(f'User {current_user_id} not found in database.')
            return

        # Create query vector
        group_values = {p: user_params.get(p, 0) for p in PARAMETERS}
        if use_weights:
            query_vec = create_group_vector_with_weights(
                group_values, PARAMETERS, weights, caps
            )
        else:
            query_vec = create_user_vector(group_values, PARAMETERS, caps)

        # Find similar groups
        exclude_id = f'g_{current_user_id}'
        recommendations = find_similar(
            session, query_vec, top_k=10, exclude_id=exclude_id
        )

        # Display recommendations with current user info
        display_recommendations(recommendations, session, current_user=user_params)

    except Exception as e:
        # Auto-rebuild indexes if vector index error
        if (
            'vector schema index' in str(e).lower()
            or 'group_vec_index' in str(e).lower()
        ):
            display_warning('Vector index missing. Rebuilding indexes...')
            try:
                from infrastructure.neo4j import (
                    ensure_constraints_and_index,
                )

                ensure_constraints_and_index(session, dims=len(PARAMETERS))
                display_info('Retrying...')
                # Retry the operation
                user_params = get_user_parameters(session, current_user_id)
                group_values = {p: user_params.get(p, 0) for p in PARAMETERS}
                if use_weights:
                    query_vec = create_group_vector_with_weights(
                        group_values, PARAMETERS, weights, caps
                    )
                else:
                    query_vec = create_user_vector(group_values, PARAMETERS, caps)
                exclude_id = f'g_{current_user_id}'
                recommendations = find_similar(
                    session, query_vec, top_k=10, exclude_id=exclude_id
                )
                display_recommendations(
                    recommendations, session, current_user=user_params
                )
            except Exception as retry_error:
                display_error(f'Failed after index rebuild: {retry_error}')
        else:
            display_error(f'Failed to get recommendations: {e}')


def action_join_group(
    session, current_user_id: str, caps: dict, use_weights: bool, weights: dict
):
    """
    Flow: Show recommendations and let user join one.

    Args:
        session: Neo4j session
        current_user_id: Current user ID
        caps: Normalization caps
        use_weights: Whether to use weighted vectors
        weights: Parameter weights
    """
    try:
        # Get user data
        user_params = get_user_parameters(session, current_user_id)

        if not user_params:
            display_error(f'User {current_user_id} not found in database.')
            return

        # Create query vector
        group_values = {p: user_params.get(p, 0) for p in PARAMETERS}
        if use_weights:
            query_vec = create_group_vector_with_weights(
                group_values, PARAMETERS, weights, caps
            )
        else:
            query_vec = create_user_vector(group_values, PARAMETERS, caps)

        # Find similar groups
        exclude_id = f'g_{current_user_id}'
        recommendations = find_similar(
            session, query_vec, top_k=10, exclude_id=exclude_id
        )

        if not recommendations:
            display_warning('No groups available to join.')
            return

        # Display recommendations
        display_recommendations(recommendations, session)

        # Loop to allow going back to recommendations
        while True:
            # Let user choose
            choices = [
                f"{i+1}. {rec['id']} ({rec.get('score', 0)*100:.1f}% match)"
                for i, rec in enumerate(recommendations)
            ]
            choices.append('Cancel')

            choice = questionary.select(
                'Which group would you like to join?', choices=choices
            ).ask()

            if choice == 'Cancel' or not choice:
                display_info('Join cancelled.')
                return

            # Extract group index
            choice_idx = int(choice.split('.')[0]) - 1
            target_group = recommendations[choice_idx]
            target_group_id = target_group['id']

            # Show detailed member info before joining
            from infrastructure.config import round_for_display

            member_params = get_group_member_parameters(session, target_group_id)

            if not member_params:
                display_error('Could not fetch group member information.')
                continue

            # Display members table with full parameters
            table = Table(
                title=f'Members of {target_group_id}',
                show_header=True,
                header_style='bold cyan',
            )
            table.add_column('Name', style='yellow')
            table.add_column('ID', style='dim')
            table.add_column('Rooms', justify='center')
            table.add_column('Roommates', justify='center')
            table.add_column('Budget', justify='right')
            table.add_column('Months', justify='center')

            for member in member_params:
                disp_rooms = round_for_display(member.get('rooms', 0))
                disp_roommates = round_for_display(member.get('roommates', 0))
                disp_budget = round_for_display(member.get('budget', 0), is_budget=True)
                disp_months = round_for_display(member.get('months', 0))

                table.add_row(
                    member.get('name', 'Unknown'),
                    member.get('id', 'N/A'),
                    str(int(disp_rooms)),
                    str(int(disp_roommates)),
                    f'₽{disp_budget:,.0f}',
                    str(int(disp_months)),
                )

            console.print('\n', table, '\n')

            # Confirm join or go back
            confirm = questionary.select(
                'What would you like to do?',
                choices=['Join this group', 'Go back to recommendations'],
            ).ask()

            if confirm == 'Go back to recommendations':
                # Show recommendations again (already calculated, no recalculation)
                display_recommendations(recommendations, session)
                continue

            # Join group
            success = add_user_to_group(
                session,
                current_user_id,
                target_group_id,
                caps=caps,
                use_weights=use_weights,
                weights=weights,
            )

            if success:
                display_success(f'Successfully joined group {target_group_id}!')
                # Show updated group info
                display_group_details(session, target_group_id)
            else:
                display_error(f'Failed to join group {target_group_id}.')

            return

    except Exception as e:
        display_error(f'Failed to join group: {e}')


def action_leave_group(
    session, current_user_id: str, caps: dict, use_weights: bool, weights: dict
):
    """
    Flow: Leave current group.

    Args:
        session: Neo4j session
        current_user_id: Current user ID
        caps: Normalization caps
        use_weights: Whether to use weighted vectors
        weights: Parameter weights
    """
    try:
        # Check current group
        current_group = get_group_by_user_id(session, current_user_id)

        if not current_group:
            display_warning('You are not in any group.')
            return

        # Show current group info
        display_group_details(session, current_group['id'])

        # Confirm
        confirm = questionary.confirm(
            'Are you sure you want to leave this group?', default=False
        ).ask()

        if not confirm:
            display_info('Leave cancelled.')
            return

        # Leave group
        new_group_id = remove_user_from_group(
            session,
            current_user_id,
            caps=caps,
            use_weights=use_weights,
            weights=weights,
        )

        if new_group_id:
            display_success(
                f'Successfully left group! Created new single-member group: {new_group_id}'
            )
        else:
            display_error('Failed to leave group.')

    except Exception as e:
        display_error(f'Failed to leave group: {e}')


def action_switch_user(session) -> Optional[str]:
    """
    Flow: Switch to different user.

    Args:
        session: Neo4j session

    Returns:
        str: New user ID or None if cancelled
    """
    try:
        # Get all users
        users = get_all_user_ids(session)

        if not users:
            display_warning('No users found in database.')
            return None

        # Create choices
        choices = [f'{name} ({user_id})' for user_id, name in users]
        choices.append('Cancel')

        choice = questionary.select('Select user to switch to:', choices=choices).ask()

        if choice == 'Cancel' or not choice:
            return None

        # Extract user ID from choice
        user_id = choice.split('(')[1].rstrip(')')
        display_success(f'Switched to user: {user_id}')
        return user_id

    except Exception as e:
        display_error(f'Failed to switch user: {e}')
        return None


def action_view_my_group(session, current_user_id: str):
    """
    Flow: Show current user's group details.

    Args:
        session: Neo4j session
        current_user_id: Current user ID
    """
    try:
        # Get current group
        current_group = get_group_by_user_id(session, current_user_id)

        if not current_group:
            display_warning('You are not in any group.')
            return

        # Display group details
        display_group_details(session, current_group['id'])

    except Exception as e:
        display_error(f'Failed to view group: {e}')


def action_view_all_groups(session, show_parameters: bool = True):
    """
    Flow: Show tree view of all groups.

    Args:
        session: Neo4j session
        show_parameters: Whether to show group parameters
    """
    try:
        display_group_tree(session, show_parameters=show_parameters)
    except Exception as e:
        display_error(f'Failed to display groups: {e}')


def action_view_statistics(session):
    """
    Flow: Show database statistics.

    Args:
        session: Neo4j session
    """
    try:
        display_statistics(session)
    except Exception as e:
        display_error(f'Failed to display statistics: {e}')


def action_create_fake_users(session, caps: dict, use_weights: bool, weights: dict):
    """
    Flow: Generate and insert fake users.

    Args:
        session: Neo4j session
        caps: Normalization caps
        use_weights: Whether to use weighted vectors
        weights: Parameter weights
    """
    try:
        # Ask which type
        user_type = questionary.select(
            'What type of users would you like to create?',
            choices=[
                'Random users (specify count)',
                'Sample users (35 predefined users)',
                'Cancel',
            ],
        ).ask()

        if user_type == 'Cancel' or not user_type:
            return

        if 'Random' in user_type:
            # Ask how many
            count_str = questionary.text(
                'How many users to generate?',
                default='10',
                validate=lambda x: x.isdigit() and int(x) > 0,
            ).ask()

            if not count_str:
                return

            count = int(count_str)
            users = generate_fake_users(count)

        else:  # Sample users
            users = sample_users()

            # Insert users
            upsert_users(
                session, users, caps=caps, use_weights=use_weights, weights=weights
            )

            # Group sample users for realistic testing

            setup_sample_groups(session, caps, use_weights, weights)

            display_success(
                f'Created {len(users)} sample users and organized them into groups!'
            )
            return

        # Insert users (for random users)
        upsert_users(
            session, users, caps=caps, use_weights=use_weights, weights=weights
        )
        display_success(f'Created {len(users)} users successfully!')

    except Exception as e:
        display_error(f'Failed to create users: {e}')


def action_clean_database(session):
    """
    Flow: Clean entire database.

    Args:
        session: Neo4j session
    """
    try:
        # Confirm
        confirm = questionary.confirm(
            '⚠️  This will delete ALL users and groups. Are you sure?', default=False
        ).ask()

        if not confirm:
            display_info('Clean cancelled.')
            return

        # Clean database
        clean_db(session)
        display_success('Database cleaned successfully!')

    except Exception as e:
        display_error(f'Failed to clean database: {e}')


def action_create_new_user(
    session, caps: dict, use_weights: bool, weights: dict
) -> Optional[str]:
    """
    Flow: Create a new user interactively (manual entry).

    Args:
        session: Neo4j session
        caps: Normalization caps
        use_weights: Whether to use weighted vectors
        weights: Parameter weights

    Returns:
        str: New user ID or None
    """
    try:
        user_data = create_user_interactive()

        if not user_data:
            return None

        # Insert user
        upsert_users(
            session, [user_data], caps=caps, use_weights=use_weights, weights=weights
        )
        display_success(f"User {user_data['id']} created successfully!")
        return user_data['id']

    except Exception as e:
        display_error(f'Failed to create user: {e}')
        return None


def action_create_new_user_main(
    session, caps: dict, use_weights: bool, weights: dict
) -> Optional[str]:
    """
    Main menu version with manual/random choice.

    Args:
        session: Neo4j session
        caps: Normalization caps
        use_weights: Whether to use weighted vectors
        weights: Parameter weights

    Returns:
        str: New user ID or None
    """
    try:
        choice = questionary.select(
            'How would you like to create the user?',
            choices=[
                'Manual (set all parameters)',
                'Randomized (auto-generate parameters)',
                'Cancel',
            ],
        ).ask()

        if choice == 'Cancel' or not choice:
            return None

        if 'Manual' in choice:
            return action_create_new_user(session, caps, use_weights, weights)
        else:
            # Generate random user
            users = generate_fake_users(1)
            user_data = users[0]
            upsert_users(
                session,
                [user_data],
                caps=caps,
                use_weights=use_weights,
                weights=weights,
            )
            display_success(f"User {user_data['id']} created with random parameters!")
            return user_data['id']
    except Exception as e:
        display_error(f'Failed to create user: {e}')
        return None


def action_rebuild_indexes(session):
    """
    Flow: Rebuild database indexes (useful if vector indexes are missing).

    Args:
        session: Neo4j session
    """
    try:
        display_info('Rebuilding database constraints and indexes...')
        ensure_constraints_and_index(session, dims=len(PARAMETERS))
        display_success('Database indexes rebuilt successfully!')

    except Exception as e:
        display_error(f'Failed to rebuild indexes: {e}')


def action_delete_my_account(
    session, current_user_id: str, caps: dict, use_weights: bool, weights: dict
) -> Optional[str]:
    """
    Flow: Delete current user account and switch to another user or create a new one.

    Args:
        session: Neo4j session
        current_user_id: Current user ID to delete
        caps: Normalization caps
        use_weights: Whether to use weighted vectors
        weights: Parameter weights

    Returns:
        str: New user ID after deletion, or None if cancelled
    """
    try:
        # Import here to avoid circular dependency
        from infrastructure.neo4j.user_ops import delete_user_form
        from infrastructure.cli.menus import select_user_with_details

        # Show warning
        display_warning(
            f'⚠️  This will permanently delete your account ({current_user_id}) and all associated data.'
        )

        # Get user's group info before deletion
        current_group = get_group_by_user_id(session, current_user_id)
        if current_group and current_group.get('member_count', 0) > 1:
            display_info(
                f"You are currently in a group with {current_group['member_count']} members. "
                "Your group will be updated after you leave."
            )

        # Confirm deletion
        confirm = questionary.confirm(
            'Are you absolutely sure you want to delete your account?', default=False
        ).ask()

        if not confirm:
            display_info('Account deletion cancelled.')
            return current_user_id

        # Double confirmation for safety
        final_confirm = questionary.text(
            f'Type "{current_user_id}" to confirm deletion:',
        ).ask()

        if final_confirm != current_user_id:
            display_warning('Confirmation failed. Account deletion cancelled.')
            return current_user_id

        # Delete the user
        delete_user_form(session, current_user_id)
        display_success(f'Account {current_user_id} has been permanently deleted.')

        # Now prompt user to select another user or create a new one
        display_info('Please select another user or create a new account:')
        new_user_id = select_user_with_details(session, caps, use_weights, weights)

        if not new_user_id:
            display_error('No user selected. Exiting...')
            return None

        return new_user_id

    except Exception as e:
        display_error(f'Failed to delete account: {e}')
        return current_user_id


def action_delete_my_group(
    session, current_user_id: str, caps: dict, use_weights: bool, weights: dict
):
    """
    Flow: Delete current group and separate all members into single-member groups.

    Args:
        session: Neo4j session
        current_user_id: Current user ID
        caps: Normalization caps
        use_weights: Whether to use weighted vectors
        weights: Parameter weights
    """
    try:
        # Check current group
        current_group = get_group_by_user_id(session, current_user_id)

        if not current_group:
            display_warning('You are not in any group.')
            return

        member_count = current_group.get('member_count', 0)

        # Show current group info
        display_group_details(session, current_group['id'])

        if member_count == 1:
            display_warning(
                'You are already in a single-member group. There is nothing to dissolve.'
            )
            return

        # Show what will happen
        display_warning(
            f'⚠️  This will dissolve the group {current_group["id"]} and '
            f'separate all {member_count} members into their own single-member groups.'
        )

        # Confirm
        confirm = questionary.confirm(
            'Are you sure you want to dissolve this group?', default=False
        ).ask()

        if not confirm:
            display_info('Group dissolution cancelled.')
            return

        # Get all member IDs before dissolution
        get_members_query = """
            MATCH (u:User)-[:MEMBER_OF]->(g:Group {id: $group_id})
            RETURN u.id as user_id, u.name as user_name
        """
        
        console.print(f'\n[cyan]🔍 DEBUG: Fetching members of group: {current_group["id"]}[/cyan]')
        result = session.run(get_members_query, group_id=current_group['id'])
        member_records = [record for record in result]
        member_ids = [record['user_id'] for record in member_records]

        console.print(f'[cyan]🔍 DEBUG: Found {len(member_ids)} member(s):[/cyan]')
        for record in member_records:
            console.print(f'[cyan]   - User ID: {record["user_id"]}, Name: {record.get("user_name", "N/A")}[/cyan]')

        if not member_ids:
            display_error('No members found in group. Something went wrong.')
            return

        display_info(f'Separating {len(member_ids)} members into individual groups...')

        # For each member, create a new single-member group
        from infrastructure.neo4j.user_ops import get_user_parameters
        from infrastructure.user_vector_utils import (
            create_group_vector_with_weights,
            create_user_vector,
        )

        # Step 1: Create all new groups for members (without touching old group yet)
        console.print(f'\n[cyan]🔍 DEBUG: STEP 1 - Creating new groups for each member[/cyan]')
        console.print(f'[cyan]   Old group ID: {current_group["id"]}[/cyan]')
        
        new_groups_created = []
        
        for member_id in member_ids:
            try:
                console.print(f'[cyan]🔍 DEBUG: Processing member: {member_id}[/cyan]')
                
                # Get user parameters
                user_params = get_user_parameters(session, member_id)
                console.print(f'[cyan]   Parameters: {user_params}[/cyan]')

                # Create new single-member group
                new_group_id = f'g_{member_id}'
                new_group_name = f'Group of {member_id}'
                
                console.print(f'[cyan]   New group ID will be: {new_group_id}[/cyan]')
                
                # CRITICAL: Check if new group ID conflicts with old group ID
                if new_group_id == current_group['id']:
                    console.print(f'[yellow]   ⚠️  Group ID matches old group! Will handle after deletion.[/yellow]')
                    # Don't create now, will be handled after old group is deleted
                    new_groups_created.append(member_id)
                    display_info(f'  ⚠️  Skipping {member_id} (owns the group being dissolved)')
                    continue

                # Create vector for new single-member group
                if use_weights:
                    new_user_vector = create_group_vector_with_weights(
                        user_params, PARAMETERS, weights, caps
                    )
                else:
                    new_user_vector = create_user_vector(user_params, PARAMETERS, caps)

                console.print(f'[cyan]   Vector created with {len(new_user_vector)} dimensions[/cyan]')

                # Create new group (don't touch old relationships yet)
                create_group_query = """
                    MERGE (g:Group {id: $new_group_id})
                    SET g.name = $group_name,
                        g.rooms = $rooms,
                        g.roommates = $roommates,
                        g.budget = $budget,
                        g.months = $months,
                        g.embedding = $embedding
                    WITH g
                    UNWIND $param_list AS param
                    MERGE (gp:GroupParameter {groupId: $new_group_id, name: param.name})
                    SET gp.value = param.value
                    MERGE (g)-[:HAS_PARAMETER]->(gp)
                    RETURN g.id as created_group_id
                """

                parameters_list = [
                    {'name': p, 'value': user_params.get(p, 0)} for p in PARAMETERS
                ]

                console.print(f'[cyan]   Executing group creation query...[/cyan]')
                result = session.run(
                    create_group_query,
                    new_group_id=new_group_id,
                    group_name=new_group_name,
                    rooms=user_params.get('rooms', 0),
                    roommates=user_params.get('roommates', 0),
                    budget=user_params.get('budget', 0),
                    months=user_params.get('months', 0),
                    embedding=new_user_vector,
                    param_list=parameters_list,
                )

                record = result.single()
                if record:
                    console.print(f'[cyan]   ✓ Query returned group ID: {record["created_group_id"]}[/cyan]')
                    new_groups_created.append(member_id)
                    display_info(f'  ✓ Created new group for {member_id}')
                else:
                    console.print(f'[red]   ✗ Query returned no result[/red]')
                    display_error(f'  ✗ Failed to create group for {member_id}')

            except Exception as e:
                console.print(f'[red]   ✗ Exception: {e}[/red]')
                display_error(f'  ✗ Failed to create group for {member_id}: {e}')
        
        console.print(f'\n[cyan]🔍 DEBUG: Groups created for {len(new_groups_created)}/{len(member_ids)} members[/cyan]')
        console.print(f'[cyan]   Created list: {new_groups_created}[/cyan]')

        # Step 2: Delete the old group first (before moving members)
        console.print(f'\n[cyan]🔍 DEBUG: STEP 2 - Deleting old group[/cyan]')
        console.print(f'[cyan]   Deleting group: {current_group["id"]}[/cyan]')
        
        if len(new_groups_created) == len(member_ids):
            delete_old_group_query = """
                MATCH (g:Group {id: $group_id})
                OPTIONAL MATCH (g)-[:HAS_PARAMETER]->(gp:GroupParameter)
                DETACH DELETE gp, g
            """
            session.run(delete_old_group_query, group_id=current_group['id'])
            console.print(f'[cyan]   ✓ Old group deleted[/cyan]')
            display_info(f'  ✓ Deleted old group {current_group["id"]}')
            
            # Step 3: Now create group for owner if needed and move all members
            console.print(f'\n[cyan]🔍 DEBUG: STEP 3 - Creating owner group and switching relationships[/cyan]')
            
            # Check if we need to create a group for the owner
            owner_id = None
            for member_id in member_ids:
                new_group_id = f'g_{member_id}'
                if new_group_id == current_group['id']:
                    owner_id = member_id
                    console.print(f'[cyan]🔍 DEBUG: Creating group for owner: {owner_id}[/cyan]')
                    
                    # Get user parameters
                    user_params = get_user_parameters(session, owner_id)
                    
                    # Create vector for new single-member group
                    if use_weights:
                        new_user_vector = create_group_vector_with_weights(
                            user_params, PARAMETERS, weights, caps
                        )
                    else:
                        new_user_vector = create_user_vector(user_params, PARAMETERS, caps)
                    
                    # Create the owner's new group
                    create_group_query = """
                        MERGE (g:Group {id: $new_group_id})
                        SET g.name = $group_name,
                            g.rooms = $rooms,
                            g.roommates = $roommates,
                            g.budget = $budget,
                            g.months = $months,
                            g.embedding = $embedding
                        WITH g
                        UNWIND $param_list AS param
                        MERGE (gp:GroupParameter {groupId: $new_group_id, name: param.name})
                        SET gp.value = param.value
                        MERGE (g)-[:HAS_PARAMETER]->(gp)
                        RETURN g.id as created_group_id
                    """
                    
                    parameters_list = [
                        {'name': p, 'value': user_params.get(p, 0)} for p in PARAMETERS
                    ]
                    
                    result = session.run(
                        create_group_query,
                        new_group_id=new_group_id,
                        group_name=f'Group of {owner_id}',
                        rooms=user_params.get('rooms', 0),
                        roommates=user_params.get('roommates', 0),
                        budget=user_params.get('budget', 0),
                        months=user_params.get('months', 0),
                        embedding=new_user_vector,
                        param_list=parameters_list,
                    )
                    
                    record = result.single()
                    if record:
                        console.print(f'[cyan]   ✓ Created owner group: {record["created_group_id"]}[/cyan]')
                        display_info(f'  ✓ Created new group for {owner_id}')
                    break
            
            display_info('Switching members to their new groups...')
            
            successfully_moved = []
            for member_id in member_ids:
                try:
                    new_group_id = f'g_{member_id}'
                    
                    console.print(f'[cyan]🔍 DEBUG: Switching {member_id}[/cyan]')
                    console.print(f'[cyan]   From group: {current_group["id"]}[/cyan]')
                    console.print(f'[cyan]   To group: {new_group_id}[/cyan]')
                    
                    # Create MEMBER_OF relationship (old group already deleted)
                    # Note: Old group and relationships were already deleted, so we just create new relationship
                    switch_query = """
                        MATCH (u:User {id: $user_id})
                        MATCH (new_g:Group {id: $new_group_id})
                        MERGE (u)-[:MEMBER_OF]->(new_g)
                        RETURN u.id as moved_user_id
                    """
                    
                    result = session.run(
                        switch_query,
                        user_id=member_id,
                        new_group_id=new_group_id
                    )
                    
                    record = result.single()
                    if record:
                        console.print(f'[cyan]   ✓ Switch successful, returned: {record["moved_user_id"]}[/cyan]')
                        successfully_moved.append(member_id)
                        display_info(f'  ✓ Moved {member_id} to new group')
                    else:
                        console.print(f'[red]   ✗ Switch query returned no result[/red]')
                        display_error(f'  ✗ Failed to move {member_id}')
                        
                except Exception as e:
                    console.print(f'[red]   ✗ Exception: {e}[/red]')
                    display_error(f'  ✗ Failed to move {member_id}: {e}')
            
            console.print(f'\n[cyan]🔍 DEBUG: Moved {len(successfully_moved)}/{len(member_ids)} members[/cyan]')
            console.print(f'[cyan]   Moved list: {successfully_moved}[/cyan]')
            
            # Check if all members were moved
            if len(successfully_moved) != len(member_ids):
                console.print(f'\n[red]🔍 DEBUG: Not all members moved successfully[/red]')
                # Some members failed to move
                failed_count = len(member_ids) - len(successfully_moved)
                display_error(
                    f'Failed to move {failed_count} member(s).'
                )
                display_warning('Some users may be without groups. Run "Repair Database" to fix.')
                return
        else:
            # Some groups failed to create
            console.print(f'\n[red]🔍 DEBUG: STEP 1 FAILED - Not all groups created[/red]')
            failed_count = len(member_ids) - len(new_groups_created)
            display_error(
                f'Failed to create groups for {failed_count} member(s). '
                f'Aborting dissolution.'
            )
            return

        console.print(f'\n[green]🔍 DEBUG: SUCCESS - All steps completed[/green]')
        display_success(
            f'Group {current_group["id"]} has been dissolved. '
            f'All {len(member_ids)} members are now in their own single-member groups.'
        )

    except Exception as e:
        display_error(f'Failed to delete group: {e}')