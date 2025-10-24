#!/usr/bin/env python3
"""
Interactive Roommate Matching CLI

Run with: 
    python -m repository.recommendation_system.cli.main
    
Or from the project root:
    python repository/recommendation_system/cli/main.py
"""
import os
import sys

# Add project root to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
repo_system_dir = os.path.dirname(current_dir)
repo_dir = os.path.dirname(repo_system_dir)
project_root = os.path.dirname(repo_dir)

sys.path.insert(0, project_root)
sys.path.insert(0, repo_dir)

import dotenv

dotenv.load_dotenv()

# Import from absolute paths to work both as module and script
from repository.recommendation_system.cli.displays import console
from repository.recommendation_system.cli.menus import main_menu, startup_menu
from repository.recommendation_system.db import (
    PARAMETERS,
    ensure_constraints_and_index,
    get_driver,
)
from repository.recommendation_system.logging_utils import setup_logger
from repository.recommendation_system.user_vector_utils import group_parameter_weights

logger = setup_logger("cli", "INFO")


def run():
    """Main entry point for interactive CLI."""

    console.print("\n" + "="*60)
    console.print("[bold cyan]🏠 Interactive Roommate Matching System[/bold cyan]")
    console.print("="*60 + "\n")

    # Configuration
    caps = {'budget': 200000, 'months': 36}
    use_weights = True
    weights = group_parameter_weights

    try:
        with get_driver() as driver:
            with driver.session() as session:
                # Ensure database setup
                logger.info("Setting up database constraints and indexes...")
                ensure_constraints_and_index(session, dims=len(PARAMETERS))

                # Startup menu
                current_user_id = startup_menu(session, caps, use_weights, weights)

                if not current_user_id:
                    console.print("[yellow]No user selected. Exiting.[/yellow]\n")
                    return

                # Run main menu loop
                main_menu(session, current_user_id, caps, use_weights, weights)

    except KeyboardInterrupt:
        console.print("\n\n[yellow]Interrupted by user. Exiting...[/yellow]\n")
    except Exception as e:
        logger.error(f"CLI Error: {e}", exc_info=True)
        console.print(f"\n[red]Error: {e}[/red]\n")


if __name__ == '__main__':
    run()

