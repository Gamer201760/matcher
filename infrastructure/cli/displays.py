"""
Display functions using rich library for beautiful terminal output.

Contains all visualization functions for users, groups, recommendations, and statistics.
"""
from typing import Dict, List, Optional

from repository.recommendation_system.config import round_for_display
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree

console = Console()


def display_user_info(user_data: Dict):
    """
    Show current user info in a panel.
    
    Args:
        user_data: User dictionary with preferences
    """
    info_text = f"""
[cyan]ID:[/cyan] {user_data.get('id', 'N/A')}
[cyan]Name:[/cyan] {user_data.get('name', 'N/A')}
[cyan]Rooms:[/cyan] {user_data.get('rooms', 0)}
[cyan]Roommates:[/cyan] {user_data.get('roommates', 0)}
[cyan]Budget:[/cyan] ₽{user_data.get('budget', 0):,}/mo
[cyan]Months:[/cyan] {user_data.get('months', 0)}
    """

    panel = Panel(
        info_text.strip(),
        title="👤 Current User",
        border_style="cyan"
    )
    console.print(panel)


def display_recommendations(recommendations: List[Dict], session, current_user: Optional[Dict] = None):
    """
    Show recommendations in a formatted table with current user at top.
    
    Args:
        recommendations: List of recommendation dictionaries
        session: Neo4j session for fetching group details
        current_user: Current user parameters (optional)
    """
    if not recommendations:
        console.print("\n[yellow]No recommendations found.[/yellow]\n")
        return

    table = Table(title="💫 Recommended Groups", show_header=True, header_style="bold magenta")
    table.add_column("#", style="cyan", width=4)
    table.add_column("Match %", justify="right", style="green")
    table.add_column("Group ID", style="yellow")
    table.add_column("Members", justify="center", style="blue")
    table.add_column("Rooms", justify="center")
    table.add_column("Roommates", justify="center")
    table.add_column("Budget", justify="right")
    table.add_column("Months", justify="center")

    from repository.recommendation_system.db import (
        get_group_info,
        get_group_member_parameters,
    )

    # Add current user row at top if provided
    if current_user:
        table.add_row(
            "YOU",
            "100%",
            "[bold]Current[/bold]",
            "—",
            f"[bold]{current_user.get('rooms', 0)}[/bold]",
            f"[bold]{current_user.get('roommates', 0)}[/bold]",
            f"[bold]₽{current_user.get('budget', 0):,}[/bold]",
            f"[bold]{current_user.get('months', 0)}[/bold]",
            style="bold cyan"
        )
        table.add_section()  # Visual separator

    for i, rec in enumerate(recommendations, 1):
        group_id = rec['id']
        group_info = get_group_info(session, group_id)

        if group_info:
            # Get actual member parameters for accurate display
            member_params = get_group_member_parameters(session, group_id)

            if member_params:
                # Calculate actual averages
                avg_rooms = sum(m.get('rooms', 0) for m in member_params) / len(member_params)
                avg_roommates = sum(m.get('roommates', 0) for m in member_params) / len(member_params)
                avg_budget = sum(m.get('budget', 0) for m in member_params) / len(member_params)
                avg_months = sum(m.get('months', 0) for m in member_params) / len(member_params)
            else:
                # Fallback to group parameters
                params = group_info.get('parameters', {})
                avg_rooms = params.get('rooms', 0)
                avg_roommates = params.get('roommates', 0)
                avg_budget = params.get('budget', 0)
                avg_months = params.get('months', 0)

            match_pct = rec.get('score', 0) * 100
            member_count = group_info.get('member_count', 0)

            # Apply rounding for display
            disp_avg_rooms = round_for_display(avg_rooms)
            disp_avg_roommates = round_for_display(avg_roommates)
            disp_avg_budget = round_for_display(avg_budget, is_budget=True)
            disp_avg_months = round_for_display(avg_months)

            # Calculate differences if current_user provided
            if current_user:
                room_diff = avg_rooms - current_user.get('rooms', 0)
                rm_diff = avg_roommates - current_user.get('roommates', 0)
                budget_diff = avg_budget - current_user.get('budget', 0)
                months_diff = avg_months - current_user.get('months', 0)

                disp_room_diff = round_for_display(room_diff)
                disp_rm_diff = round_for_display(rm_diff)
                disp_budget_diff = round_for_display(budget_diff, is_budget=True)
                disp_months_diff = round_for_display(months_diff)

                rooms_display = f"{disp_avg_rooms} [dim]({disp_room_diff:+g})[/dim]"
                rm_display = f"{disp_avg_roommates} [dim]({disp_rm_diff:+g})[/dim]"
                budget_display = f"₽{disp_avg_budget:,.0f} [dim]({disp_budget_diff:+,.0f})[/dim]"
                months_display = f"{disp_avg_months} [dim]({disp_months_diff:+g})[/dim]"
            else:
                rooms_display = f"{disp_avg_rooms}"
                rm_display = f"{disp_avg_roommates}"
                budget_display = f"₽{disp_avg_budget:,.0f}"
                months_display = f"{disp_avg_months}"

            table.add_row(
                str(i),
                f"{match_pct:.1f}%",
                group_id,
                str(member_count),
                rooms_display,
                rm_display,
                budget_display,
                months_display
            )

    console.print("\n", table, "\n")


def display_group_tree(session, max_groups: Optional[int] = None, show_parameters: bool = True):
    """
    Display all groups in a tree structure (like Linux 'tree' command).
    
    Args:
        session: Neo4j session
        max_groups: Maximum number of groups to display
        show_parameters: Whether to show group parameters
    
    Example output:
    Groups/
    ├── g_user1 (2 members) — rooms: 2, roommates: 1, budget: ₽15000/mo, months: 12
    │   ├── Alice — rooms:2 rm:1 ₽15,000/mo 12mo
    │   └── Bob — rooms:2 rm:1 ₽14,000/mo 12mo
    └── g_user3 (1 member) — rooms: 1, roommates: 0, budget: ₽8000/mo, months: 6
        └── Charlie — rooms:1 rm:0 ₽8,000/mo 6mo
    """
    # Query all groups with their members AND member parameters from Parameter nodes
    query = """
        MATCH (g:Group)
        OPTIONAL MATCH (g)<-[:MEMBER_OF]-(u:User)
        OPTIONAL MATCH (u)-[:HAS_PARAMETER]->(p:Parameter)
        WITH g, u, 
             collect({name: p.name, value: p.value}) as params
        WITH g, 
             count(DISTINCT u) as member_count,
             collect(DISTINCT {
                 id: u.id, 
                 name: u.name,
                 rooms: [param IN params WHERE param.name = 'rooms'][0].value,
                 roommates: [param IN params WHERE param.name = 'roommates'][0].value,
                 budget: [param IN params WHERE param.name = 'budget'][0].value,
                 months: [param IN params WHERE param.name = 'months'][0].value
             }) as members
        WHERE member_count > 0
        RETURN g.id as group_id, 
               g.rooms as rooms, 
               g.roommates as roommates,
               g.budget as budget, 
               g.months as months,
               member_count,
               members
        ORDER BY member_count DESC, g.id
        LIMIT $max_groups
    """

    result = session.run(query, max_groups=max_groups or 1000)
    groups = list(result)

    # Filter out broken groups (all params are 0 or None)
    filtered_groups = []
    for group in groups:
        rooms = group['rooms'] if group['rooms'] is not None else 0
        roommates = group['roommates'] if group['roommates'] is not None else 0
        budget = group['budget'] if group['budget'] is not None else 0
        months = group['months'] if group['months'] is not None else 0

        # Keep groups that have at least one non-zero parameter
        if not (rooms == 0 and roommates == 0 and budget == 0 and months == 0):
            filtered_groups.append(group)

    if not filtered_groups:
        console.print("\n[yellow]No valid groups found in database.[/yellow]\n")
        return

    # Create tree
    tree = Tree(f"[bold cyan]📊 Groups/[/bold cyan] [dim]({len(filtered_groups)} total)[/dim]")

    for group in filtered_groups:
        # Group branch
        group_id = group['group_id']
        member_count = group['member_count']

        if show_parameters:
            rooms = group['rooms'] if group['rooms'] is not None else 0
            roommates = group['roommates'] if group['roommates'] is not None else 0
            budget = group['budget'] if group['budget'] is not None else 0
            months = group['months'] if group['months'] is not None else 0

            # Apply rounding for display
            disp_rooms = round_for_display(rooms)
            disp_roommates = round_for_display(roommates)
            disp_budget = round_for_display(budget, is_budget=True)
            disp_months = round_for_display(months)

            group_label = (
                f"[green]{group_id}[/green] [dim]({member_count} member{'s' if member_count != 1 else ''})[/dim] — "
                f"rooms: {disp_rooms}, "
                f"roommates: {disp_roommates}, "
                f"budget: ₽{disp_budget:,.0f}/mo, "
                f"months: {disp_months}"
            )
        else:
            group_label = f"[green]{group_id}[/green] [dim]({member_count} member{'s' if member_count != 1 else ''})[/dim]"

        group_branch = tree.add(group_label)

        # Add members with their parameters (different color)
        members = group['members']
        for member in members:
            if member['id']:  # Only add if member exists
                # Handle None values with defaults
                rooms = member['rooms'] if member['rooms'] is not None else 0
                roommates = member['roommates'] if member['roommates'] is not None else 0
                budget = member['budget'] if member['budget'] is not None else 0
                months = member['months'] if member['months'] is not None else 0

                # Apply rounding for display
                disp_rooms = round_for_display(rooms)
                disp_roommates = round_for_display(roommates)
                disp_budget = round_for_display(budget, is_budget=True)
                disp_months = round_for_display(months)

                # Show member parameters in magenta instead of IDs
                member_params = (
                    f"[magenta]rooms:{int(disp_rooms)} rm:{int(disp_roommates)} "
                    f"₽{disp_budget:,.0f}/mo {int(disp_months)}mo[/magenta]"
                )
                member_label = f"[yellow]{member['name'] or 'Unknown'}[/yellow] {member_params}"
                group_branch.add(member_label)

    console.print("\n", tree, "\n")


def display_group_details(session, group_id: str):
    """
    Show detailed group info with members and parameters.
    
    Args:
        session: Neo4j session
        group_id: Group ID to display
    """
    from repository.recommendation_system.db import (
        get_group_info,
        get_group_member_parameters,
    )

    group_info = get_group_info(session, group_id)

    if not group_info:
        console.print(f"\n[red]Group {group_id} not found.[/red]\n")
        return

    # Get member parameters for accurate averages
    member_params = get_group_member_parameters(session, group_id)

    if member_params:
        avg_rooms = sum(m.get('rooms', 0) for m in member_params) / len(member_params)
        avg_roommates = sum(m.get('roommates', 0) for m in member_params) / len(member_params)
        avg_budget = sum(m.get('budget', 0) for m in member_params) / len(member_params)
        avg_months = sum(m.get('months', 0) for m in member_params) / len(member_params)
    else:
        params = group_info.get('parameters', {})
        avg_rooms = params.get('rooms', 0)
        avg_roommates = params.get('roommates', 0)
        avg_budget = params.get('budget', 0)
        avg_months = params.get('months', 0)

    # Apply rounding for display
    disp_avg_rooms = round_for_display(avg_rooms)
    disp_avg_roommates = round_for_display(avg_roommates)
    disp_avg_budget = round_for_display(avg_budget, is_budget=True)
    disp_avg_months = round_for_display(avg_months)

    # Group info text
    info_text = f"""
[cyan]Group ID:[/cyan] {group_id}
[cyan]Members:[/cyan] {group_info.get('member_count', 0)}
[cyan]Avg Rooms:[/cyan] {disp_avg_rooms}
[cyan]Avg Roommates:[/cyan] {disp_avg_roommates}
[cyan]Avg Budget:[/cyan] ₽{disp_avg_budget:,.0f}/mo
[cyan]Avg Months:[/cyan] {disp_avg_months}
    """

    panel = Panel(
        info_text.strip(),
        title=f"👥 Group: {group_id}",
        border_style="green"
    )
    console.print("\n", panel)

    # Members table
    if group_info.get('members'):
        table = Table(title="Members", show_header=True, header_style="bold cyan")
        table.add_column("Name", style="yellow")
        table.add_column("ID", style="dim")

        for member in group_info['members']:
            table.add_row(
                member.get('name', 'Unknown'),
                member.get('id', 'N/A')
            )

        console.print(table, "\n")


def display_statistics(session):
    """
    Show database statistics.
    
    Args:
        session: Neo4j session
    """
    # Query statistics
    stats_query = """
        MATCH (u:User)
        WITH count(u) as total_users
        MATCH (g:Group)
        WITH total_users, count(g) as total_groups
        MATCH (g:Group)<-[:MEMBER_OF]-(u:User)
        WITH total_users, total_groups, g, count(u) as member_count
        RETURN total_users,
               total_groups,
               avg(member_count) as avg_group_size,
               max(member_count) as max_group_size,
               min(member_count) as min_group_size
    """

    result = session.run(stats_query)
    stats = result.single()

    if not stats:
        console.print("\n[yellow]No data in database.[/yellow]\n")
        return

    # Apply rounding for display
    disp_avg_group_size = round_for_display(stats['avg_group_size'])

    # Create statistics panel
    stats_text = f"""
[cyan]Total Users:[/cyan] {stats['total_users']}
[cyan]Total Groups:[/cyan] {stats['total_groups']}
[cyan]Avg Group Size:[/cyan] {disp_avg_group_size} members
[cyan]Largest Group:[/cyan] {stats['max_group_size']} members
[cyan]Smallest Group:[/cyan] {stats['min_group_size']} member(s)
    """

    panel = Panel(
        stats_text.strip(),
        title="📊 Database Statistics",
        border_style="magenta"
    )
    console.print("\n", panel, "\n")


def display_success(message: str):
    """Display a success message."""
    console.print(f"\n[green]✓ {message}[/green]\n")


def display_error(message: str):
    """Display an error message."""
    console.print(f"\n[red]✗ {message}[/red]\n")


def display_warning(message: str):
    """Display a warning message."""
    console.print(f"\n[yellow]⚠ {message}[/yellow]\n")


def display_info(message: str):
    """Display an info message."""
    console.print(f"\n[cyan]ℹ {message}[/cyan]\n")

