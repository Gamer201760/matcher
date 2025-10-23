"""
Menu system for interactive CLI.

Contains the main menu loop and startup configuration menu.
"""
import questionary
from typing import Optional
from repository.recommendation_system.cli.actions import (
    action_get_recommendations, action_join_group, action_leave_group,
    action_switch_user, action_view_my_group, action_view_all_groups,
    action_view_statistics, action_create_fake_users, action_clean_database,
    action_create_new_user, action_create_new_user_main, action_rebuild_indexes
)
from repository.recommendation_system.cli.displays import console, display_info, display_error
from repository.recommendation_system.cli.utils import get_all_user_ids, sample_users, generate_fake_users, setup_sample_groups, auto_group_users
from repository.recommendation_system.db import clean_db, upsert_users


def main_menu(session, current_user_id: str, caps: dict, use_weights: bool, weights: dict) -> str:
    """
    Main menu loop - runs until user exits.
    
    Args:
        session: Neo4j session
        current_user_id: Current user ID
        caps: Normalization caps
        use_weights: Whether to use weighted vectors
        weights: Parameter weights
        
    Returns:
        str: Current user ID (may have changed via switch user)
    """
    while True:
        # Show current user context with name
        user_query = "MATCH (u:User {id: $user_id}) RETURN u.name as name"
        result = session.run(user_query, user_id=current_user_id)
        user_record = result.single()
        user_name = user_record['name'] if user_record else 'Unknown'
        
        console.print(f"\n[bold cyan]Current User:[/bold cyan] [yellow]{user_name}[/yellow] [dim]({current_user_id})[/dim]")
        
        # Check if user is in a group
        from repository.recommendation_system.db import get_group_by_user_id
        current_group = get_group_by_user_id(session, current_user_id)
        is_in_group = current_group is not None
        
        # Build menu choices dynamically
        choices = [
            "🔍 Get Recommendations",
        ]
        
        # Only show Join if NOT in a group
        if not is_in_group:
            choices.append("🤝 Join a Group")
        
        choices.extend([
            "🚪 Leave My Group",
            "👁️  View My Group",
            "🌳 View All Groups (Tree)",
            "👤 Switch User",
            "➕ Create New User",
            "📊 View Statistics",
            "➕ Add Fake Users",
            "🧹 Clean Database",
            "❌ Exit"
        ])
        
        choice = questionary.select(
            "🏠 Roommate Matcher - Main Menu",
            choices=choices
        ).ask()
        
        if not choice:
            continue
        
        if choice == "🔍 Get Recommendations":
            action_get_recommendations(session, current_user_id, caps, use_weights, weights)
            
        elif choice == "🤝 Join a Group":
            action_join_group(session, current_user_id, caps, use_weights, weights)
            
        elif choice == "🚪 Leave My Group":
            action_leave_group(session, current_user_id, caps, use_weights, weights)
            
        elif choice == "👁️  View My Group":
            action_view_my_group(session, current_user_id)
            
        elif choice == "🌳 View All Groups (Tree)":
            action_view_all_groups(session, show_parameters=True)
            
        elif choice == "👤 Switch User":
            new_user_id = action_switch_user(session)
            if new_user_id:
                current_user_id = new_user_id
        
        elif choice == "➕ Create New User":
            new_user_id = action_create_new_user_main(session, caps, use_weights, weights)
            if new_user_id:
                display_info(f"Would you like to switch to the new user {new_user_id}?")
                switch = questionary.confirm("Switch to new user?", default=True).ask()
                if switch:
                    current_user_id = new_user_id
                
        elif choice == "📊 View Statistics":
            action_view_statistics(session)
            
        elif choice == "➕ Add Fake Users":
            action_create_fake_users(session, caps, use_weights, weights)
            
        elif choice == "🧹 Clean Database":
            action_clean_database(session)
            
        elif choice == "❌ Exit":
            console.print("\n[green]👋 Thanks for using Roommate Matcher![/green]\n")
            break
    
    return current_user_id


def select_user_with_details(session, caps: dict, use_weights: bool, weights: dict) -> Optional[str]:
    """Select user showing their parameters and group status."""
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
        display_error("No users found. Please restart and create users.")
        return None
    
    # Format choices with parameters
    choices = []
    
    # Add "Create New User" option at the TOP for visibility
    choices.append("➕ Create New User")
    
    for user in users:
        group_info = ""
        if user['group_id']:
            group_info = f"[green]in group ({user['group_size']} members)[/green]"
        else:
            group_info = "[dim]solo[/dim]"
        
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
        "Select your user (or create a new one):",
        choices=choices
    ).ask()
    
    if not choice:
        return None
    
    if "Create New User" in choice:
        return action_create_new_user_main(session, caps, use_weights, weights)
    
    # Extract user ID from choice (find matching user)
    # Note: choices[0] is "Create New User", so user choices start at index 1
    for i, user in enumerate(users):
        if choices[i + 1] == choice:  # +1 because choices[0] is "Create New User"
            return user['id']
    
    return None


def startup_menu(session, caps: dict, use_weights: bool, weights: dict) -> Optional[str]:
    """
    Improved startup flow.
    
    Args:
        session: Neo4j session
        caps: Normalization caps
        use_weights: Whether to use weighted vectors
        weights: Parameter weights
        
    Returns:
        str: User ID to start with, or None
    """
    # Ask about database cleanup
    clean = questionary.confirm(
        "Clean database before starting?",
        default=False
    ).ask()
    
    if clean:
        clean_db()
        console.print("[green]✓ Database cleaned[/green]")
        
        # Auto-create sample users
        console.print("[cyan]Creating sample users...[/cyan]")
        users = sample_users()
        # Allow customizing count
        count_choice = questionary.text(
            f"How many sample users to create? (default: {len(users)})",
            default=str(len(users)),
            validate=lambda x: x.isdigit() and int(x) > 0
        ).ask()
        
        if not count_choice:
            return None
        
        if int(count_choice) != len(users):
            users = generate_fake_users(int(count_choice))
        else:
            users = sample_users()
        
        upsert_users(session, users, caps=caps, use_weights=use_weights, weights=weights)
        
        # Group them if using sample users
        if len(users) == 35:
            setup_sample_groups(session, caps, use_weights, weights)
        else:
            # Group random users probabilistically
            auto_group_users(session, users, caps, use_weights, weights)
        
        console.print(f"[green]✓ Created {len(users)} users[/green]")
    
    # Show enhanced user selection with parameters
    return select_user_with_details(session, caps, use_weights, weights)

