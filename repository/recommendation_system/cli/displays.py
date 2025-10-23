"""
Display functions using rich library for beautiful terminal output.

Contains all visualization functions for users, groups, recommendations, and statistics.
"""
from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from rich.panel import Panel
from rich.text import Text
from typing import List, Dict, Optional

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


def display_recommendations(recommendations: List[Dict], session):
    """
    Show recommendations in a formatted table.
    
    Args:
        recommendations: List of recommendation dictionaries
        session: Neo4j session for fetching group details
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
    
    from repository.recommendation_system.db import get_group_info, get_group_member_parameters
    
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
            
            table.add_row(
                str(i),
                f"{match_pct:.1f}%",
                group_id,
                str(member_count),
                f"{avg_rooms:.1f}",
                f"{avg_roommates:.1f}",
                f"₽{avg_budget:,.0f}",
                f"{avg_months:.1f}"
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
    │   ├── Alice (user1)
    │   └── Bob (user2)
    └── g_user3 (1 member) — rooms: 1, roommates: 0, budget: ₽8000/mo, months: 6
        └── Charlie (user3)
    """
    # Query all groups with their members
    query = """
        MATCH (g:Group)
        OPTIONAL MATCH (g)<-[:MEMBER_OF]-(u:User)
        WITH g, count(u) as member_count, collect({id: u.id, name: u.name}) as members
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
    
    if not groups:
        console.print("\n[yellow]No groups found in database.[/yellow]\n")
        return
    
    # Create tree
    tree = Tree(f"[bold cyan]📊 Groups/[/bold cyan] [dim]({len(groups)} total)[/dim]")
    
    for group in groups:
        # Group branch
        group_id = group['group_id']
        member_count = group['member_count']
        
        if show_parameters:
            rooms = group['rooms'] if group['rooms'] is not None else 0
            roommates = group['roommates'] if group['roommates'] is not None else 0
            budget = group['budget'] if group['budget'] is not None else 0
            months = group['months'] if group['months'] is not None else 0
            
            group_label = (
                f"[green]{group_id}[/green] [dim]({member_count} member{'s' if member_count != 1 else ''})[/dim] — "
                f"rooms: {rooms}, "
                f"roommates: {roommates}, "
                f"budget: ₽{budget:,}/mo, "
                f"months: {months}"
            )
        else:
            group_label = f"[green]{group_id}[/green] [dim]({member_count} member{'s' if member_count != 1 else ''})[/dim]"
        
        group_branch = tree.add(group_label)
        
        # Add members
        members = group['members']
        for member in members:
            if member['id']:  # Only add if member exists
                member_label = f"[yellow]{member['name'] or 'Unknown'}[/yellow] [dim]({member['id']})[/dim]"
                group_branch.add(member_label)
    
    console.print("\n", tree, "\n")


def display_group_details(session, group_id: str):
    """
    Show detailed group info with members and parameters.
    
    Args:
        session: Neo4j session
        group_id: Group ID to display
    """
    from repository.recommendation_system.db import get_group_info, get_group_member_parameters
    
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
    
    # Group info text
    info_text = f"""
[cyan]Group ID:[/cyan] {group_id}
[cyan]Members:[/cyan] {group_info.get('member_count', 0)}
[cyan]Avg Rooms:[/cyan] {avg_rooms:.1f}
[cyan]Avg Roommates:[/cyan] {avg_roommates:.1f}
[cyan]Avg Budget:[/cyan] ₽{avg_budget:,.0f}/mo
[cyan]Avg Months:[/cyan] {avg_months:.1f}
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
    
    # Create statistics panel
    stats_text = f"""
[cyan]Total Users:[/cyan] {stats['total_users']}
[cyan]Total Groups:[/cyan] {stats['total_groups']}
[cyan]Avg Group Size:[/cyan] {stats['avg_group_size']:.2f} members
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

