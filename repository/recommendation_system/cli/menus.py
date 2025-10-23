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
    action_create_new_user, action_rebuild_indexes
)
from repository.recommendation_system.cli.displays import console, display_info
from repository.recommendation_system.cli.utils import get_all_user_ids, sample_users
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
        # Show current user context
        console.print(f"\n[bold cyan]Current User:[/bold cyan] [yellow]{current_user_id}[/yellow]")
        
        choice = questionary.select(
            "🏠 Roommate Matcher - Main Menu",
            choices=[
                "🔍 Get Recommendations",
                "🤝 Join a Group",
                "🚪 Leave My Group",
                "👁️  View My Group",
                "🌳 View All Groups (Tree)",
                "👤 Switch User",
                "📊 View Statistics",
                "➕ Add Fake Users",
                "🔧 Rebuild Indexes",
                "🧹 Clean Database",
                "❌ Exit"
            ]
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
                
        elif choice == "📊 View Statistics":
            action_view_statistics(session)
            
        elif choice == "➕ Add Fake Users":
            action_create_fake_users(session, caps, use_weights, weights)
            
        elif choice == "🔧 Rebuild Indexes":
            action_rebuild_indexes(session)
            
        elif choice == "🧹 Clean Database":
            action_clean_database(session)
            
        elif choice == "❌ Exit":
            console.print("\n[green]👋 Thanks for using Roommate Matcher![/green]\n")
            break
    
    return current_user_id


def startup_menu(session, caps: dict, use_weights: bool, weights: dict) -> Optional[str]:
    """
    Initial setup menu before main loop.
    
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
    
    # Check if there are existing users
    users = get_all_user_ids(session)
    
    if users:
        # Users exist, give options
        create_choice = questionary.select(
            "How would you like to start?",
            choices=[
                "Select existing user",
                "Create a new user",
                "Generate sample users first",
                "Exit"
            ]
        ).ask()
    else:
        # No users, must create
        create_choice = questionary.select(
            "No users found in database. How would you like to start?",
            choices=[
                "Create a new user",
                "Generate sample users first",
                "Exit"
            ]
        ).ask()
    
    if create_choice == "Exit" or not create_choice:
        return None
    
    if create_choice == "Select existing user":
        return action_switch_user(session)
        
    elif create_choice == "Create a new user":
        user_id = action_create_new_user(session, caps, use_weights, weights)
        return user_id
        
    elif create_choice == "Generate sample users first":
        # Generate sample users
        users = sample_users()
        upsert_users(session, users, caps=caps, use_weights=use_weights, weights=weights)
        
        # Group sample users for realistic testing
        from repository.recommendation_system.cli.utils import setup_sample_groups
        setup_sample_groups(session, caps, use_weights, weights)
        
        console.print(f"[green]✓ Created {len(users)} sample users and organized them into groups[/green]")
        
        # Now let user select one
        return action_switch_user(session)
    
    return None

