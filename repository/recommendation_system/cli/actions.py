"""
Action handlers for user interactions.

Contains all the flow logic for menu actions like joining groups,
getting recommendations, switching users, etc.
"""
import questionary
from typing import Optional
from repository.recommendation_system.cli.displays import (
    console, display_recommendations, display_group_details,
    display_group_tree, display_statistics, display_user_info,
    display_success, display_error, display_warning, display_info
)
from repository.recommendation_system.cli.utils import generate_fake_users, sample_users, create_user_interactive, get_all_user_ids
from repository.recommendation_system.db import (
    get_user_parameters, find_similar, add_user_to_group,
    remove_user_from_group, get_group_info, upsert_users,
    clean_db, PARAMETERS, get_group_by_user_id
)
from repository.recommendation_system.user_vector_utils import create_user_vector, create_group_vector_with_weights


def action_get_recommendations(session, current_user_id: str, caps: dict, use_weights: bool, weights: dict):
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
            display_error(f"User {current_user_id} not found in database.")
            return
        
        # Create query vector
        group_values = {p: user_params.get(p, 0) for p in PARAMETERS}
        if use_weights:
            query_vec = create_group_vector_with_weights(group_values, PARAMETERS, weights, caps)
        else:
            query_vec = create_user_vector(group_values, PARAMETERS, caps)
        
        # Find similar groups
        exclude_id = f"g_{current_user_id}"
        recommendations = find_similar(session, query_vec, top_k=10, exclude_id=exclude_id)
        
        # Display recommendations with current user info
        display_recommendations(recommendations, session, current_user=user_params)
        
    except Exception as e:
        # Auto-rebuild indexes if vector index error
        if "vector schema index" in str(e).lower() or "group_vec_index" in str(e).lower():
            display_warning("Vector index missing. Rebuilding indexes...")
            try:
                from repository.recommendation_system.db import ensure_constraints_and_index
                ensure_constraints_and_index(session, dims=len(PARAMETERS))
                display_info("Retrying...")
                # Retry the operation
                user_params = get_user_parameters(session, current_user_id)
                group_values = {p: user_params.get(p, 0) for p in PARAMETERS}
                if use_weights:
                    query_vec = create_group_vector_with_weights(group_values, PARAMETERS, weights, caps)
                else:
                    query_vec = create_user_vector(group_values, PARAMETERS, caps)
                exclude_id = f"g_{current_user_id}"
                recommendations = find_similar(session, query_vec, top_k=10, exclude_id=exclude_id)
                display_recommendations(recommendations, session, current_user=user_params)
            except Exception as retry_error:
                display_error(f"Failed after index rebuild: {retry_error}")
        else:
            display_error(f"Failed to get recommendations: {e}")


def action_join_group(session, current_user_id: str, caps: dict, use_weights: bool, weights: dict):
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
            display_error(f"User {current_user_id} not found in database.")
            return
        
        # Create query vector
        group_values = {p: user_params.get(p, 0) for p in PARAMETERS}
        if use_weights:
            query_vec = create_group_vector_with_weights(group_values, PARAMETERS, weights, caps)
        else:
            query_vec = create_user_vector(group_values, PARAMETERS, caps)
        
        # Find similar groups
        exclude_id = f"g_{current_user_id}"
        recommendations = find_similar(session, query_vec, top_k=10, exclude_id=exclude_id)
        
        if not recommendations:
            display_warning("No groups available to join.")
            return
        
        # Display recommendations
        display_recommendations(recommendations, session)
        
        # Loop to allow going back to recommendations
        while True:
            # Let user choose
            choices = [f"{i+1}. {rec['id']} ({rec.get('score', 0)*100:.1f}% match)" 
                       for i, rec in enumerate(recommendations)]
            choices.append("Cancel")
            
            choice = questionary.select(
                "Which group would you like to join?",
                choices=choices
            ).ask()
            
            if choice == "Cancel" or not choice:
                display_info("Join cancelled.")
                return
            
            # Extract group index
            choice_idx = int(choice.split('.')[0]) - 1
            target_group = recommendations[choice_idx]
            target_group_id = target_group['id']
            
            # Show detailed member info before joining
            from repository.recommendation_system.db import get_group_member_parameters
            from repository.recommendation_system.config import round_for_display
            
            member_params = get_group_member_parameters(session, target_group_id)
            
            if not member_params:
                display_error("Could not fetch group member information.")
                continue
            
            # Display members table with full parameters
            table = Table(title=f"Members of {target_group_id}", show_header=True, header_style="bold cyan")
            table.add_column("Name", style="yellow")
            table.add_column("ID", style="dim")
            table.add_column("Rooms", justify="center")
            table.add_column("Roommates", justify="center")
            table.add_column("Budget", justify="right")
            table.add_column("Months", justify="center")
            
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
                    f"₽{disp_budget:,.0f}",
                    str(int(disp_months))
                )
            
            console.print("\n", table, "\n")
            
            # Confirm join or go back
            confirm = questionary.select(
                "What would you like to do?",
                choices=[
                    "Join this group",
                    "Go back to recommendations"
                ]
            ).ask()
            
            if confirm == "Go back to recommendations":
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
                weights=weights
            )
            
            if success:
                display_success(f"Successfully joined group {target_group_id}!")
                # Show updated group info
                display_group_details(session, target_group_id)
            else:
                display_error(f"Failed to join group {target_group_id}.")
            
            return
            
    except Exception as e:
        display_error(f"Failed to join group: {e}")


def action_leave_group(session, current_user_id: str, caps: dict, use_weights: bool, weights: dict):
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
            display_warning("You are not in any group.")
            return
        
        # Show current group info
        display_group_details(session, current_group['id'])
        
        # Confirm
        confirm = questionary.confirm(
            "Are you sure you want to leave this group?",
            default=False
        ).ask()
        
        if not confirm:
            display_info("Leave cancelled.")
            return
        
        # Leave group
        new_group_id = remove_user_from_group(
            session,
            current_user_id,
            caps=caps,
            use_weights=use_weights,
            weights=weights
        )
        
        if new_group_id:
            display_success(f"Successfully left group! Created new single-member group: {new_group_id}")
        else:
            display_error("Failed to leave group.")
            
    except Exception as e:
        display_error(f"Failed to leave group: {e}")


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
            display_warning("No users found in database.")
            return None
        
        # Create choices
        choices = [f"{name} ({user_id})" for user_id, name in users]
        choices.append("Cancel")
        
        choice = questionary.select(
            "Select user to switch to:",
            choices=choices
        ).ask()
        
        if choice == "Cancel" or not choice:
            return None
        
        # Extract user ID from choice
        user_id = choice.split('(')[1].rstrip(')')
        display_success(f"Switched to user: {user_id}")
        return user_id
        
    except Exception as e:
        display_error(f"Failed to switch user: {e}")
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
            display_warning("You are not in any group.")
            return
        
        # Display group details
        display_group_details(session, current_group['id'])
        
    except Exception as e:
        display_error(f"Failed to view group: {e}")


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
        display_error(f"Failed to display groups: {e}")


def action_view_statistics(session):
    """
    Flow: Show database statistics.
    
    Args:
        session: Neo4j session
    """
    try:
        display_statistics(session)
    except Exception as e:
        display_error(f"Failed to display statistics: {e}")


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
            "What type of users would you like to create?",
            choices=[
                "Random users (specify count)",
                "Sample users (35 predefined users)",
                "Cancel"
            ]
        ).ask()
        
        if user_type == "Cancel" or not user_type:
            return
        
        if "Random" in user_type:
            # Ask how many
            count_str = questionary.text(
                "How many users to generate?",
                default="10",
                validate=lambda x: x.isdigit() and int(x) > 0
            ).ask()
            
            if not count_str:
                return
            
            count = int(count_str)
            users = generate_fake_users(count)
            
        else:  # Sample users
            users = sample_users()
            
            # Insert users
            upsert_users(session, users, caps=caps, use_weights=use_weights, weights=weights)
            
            # Group sample users for realistic testing
            from repository.recommendation_system.cli.utils import setup_sample_groups
            setup_sample_groups(session, caps, use_weights, weights)
            
            display_success(f"Created {len(users)} sample users and organized them into groups!")
            return
        
        # Insert users (for random users)
        upsert_users(session, users, caps=caps, use_weights=use_weights, weights=weights)
        display_success(f"Created {len(users)} users successfully!")
        
    except Exception as e:
        display_error(f"Failed to create users: {e}")


def action_clean_database(session):
    """
    Flow: Clean entire database.
    
    Args:
        session: Neo4j session
    """
    try:
        # Confirm
        confirm = questionary.confirm(
            "⚠️  This will delete ALL users and groups. Are you sure?",
            default=False
        ).ask()
        
        if not confirm:
            display_info("Clean cancelled.")
            return
        
        # Clean database
        clean_db()
        display_success("Database cleaned successfully!")
        
    except Exception as e:
        display_error(f"Failed to clean database: {e}")


def action_create_new_user(session, caps: dict, use_weights: bool, weights: dict) -> Optional[str]:
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
        upsert_users(session, [user_data], caps=caps, use_weights=use_weights, weights=weights)
        display_success(f"User {user_data['id']} created successfully!")
        return user_data['id']
        
    except Exception as e:
        display_error(f"Failed to create user: {e}")
        return None


def action_create_new_user_main(session, caps: dict, use_weights: bool, weights: dict) -> Optional[str]:
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
            "How would you like to create the user?",
            choices=[
                "Manual (set all parameters)",
                "Randomized (auto-generate parameters)",
                "Cancel"
            ]
        ).ask()
        
        if choice == "Cancel" or not choice:
            return None
        
        if "Manual" in choice:
            return action_create_new_user(session, caps, use_weights, weights)
        else:
            # Generate random user
            users = generate_fake_users(1)
            user_data = users[0]
            upsert_users(session, [user_data], caps=caps, use_weights=use_weights, weights=weights)
            display_success(f"User {user_data['id']} created with random parameters!")
            return user_data['id']
    except Exception as e:
        display_error(f"Failed to create user: {e}")
        return None


def action_rebuild_indexes(session):
    """
    Flow: Rebuild database indexes (useful if vector indexes are missing).
    
    Args:
        session: Neo4j session
    """
    try:
        from repository.recommendation_system.db import ensure_constraints_and_index, PARAMETERS
        
        display_info("Rebuilding database constraints and indexes...")
        ensure_constraints_and_index(session, dims=len(PARAMETERS))
        display_success("Database indexes rebuilt successfully!")
        
    except Exception as e:
        display_error(f"Failed to rebuild indexes: {e}")

