"""
Utility functions for the interactive CLI.

Contains helper functions for user generation, database queries, and interactive input.
"""
import random
import uuid
from typing import Dict, List, Optional

import questionary


def generate_fake_users(count: int) -> List[Dict]:
    """
    Generate random users with realistic preferences for simulation.
    
    Each user gets a unique UUID as their ID.
    
    Args:
        count: Number of fake users to generate
        
    Returns:
        list: List of user dictionaries with random preferences
    """
    names = [
        # Original names
        'Alex', 'Bailey', 'Cameron', 'Dakota', 'Eden', 'Finley', 'Gray', 'Harper',
        'Iris', 'Jordan', 'Kennedy', 'Logan', 'Morgan', 'Nico', 'Oakley', 'Parker',
        'Quinn', 'Riley', 'Sage', 'Taylor', 'Uma', 'Val', 'Winter', 'Xen', 'Yuki',
        'Zara', 'Andy', 'Blake', 'Casey', 'Drew', 'Ellis', 'Frankie', 'Gene', 'Hayden',
        # New names (40 more)
        'Avery', 'Brooklyn', 'Charlie', 'Devin', 'Emerson', 'Finley', 'Grey',
        'Harley', 'Indigo', 'Jamie', 'Kai', 'Lane', 'Maven', 'Nova', 'Ocean',
        'Phoenix', 'River', 'Skylar', 'True', 'Azure', 'Blu', 'Cedar', 'Delta',
        'Echo', 'Fox', 'Haven', 'Jett', 'Kit', 'Lake', 'Marley', 'North',
        'Onyx', 'Poet', 'Quest', 'Raven', 'Story', 'Timber', 'Unity', 'Wren',
        'Ever', 'Zion', 'Arrow', 'Bear', 'Cloud', 'Dawn', 'Ember', 'Frost'
    ]

    users = []
    for i in range(count):
        # Generate UUID for each user
        user_id = str(uuid.uuid4())
        name = random.choice(names) if i < len(names) else names[i % len(names)]

        # Ensure no 0 values - all parameters must be > 0
        users.append({
            'id': user_id,
            'name': f'{name} {i+1}' if count > len(names) else name,
            'rooms': random.randint(1, 4),
            'roommates': random.randint(1, 5),  # At least 1
            'budget': random.randint(5000, 60000),
            'months': random.choice([3, 6, 9, 12, 18, 24, 36])
        })

    return users


def sample_users() -> List[Dict]:
    """
    Generate a diverse set of test users for recommendation testing.
    
    Uses random UUIDs for each user.
    
    Returns:
        list: List of 35 predefined test users with varied preferences
    """
    
    users_data = [
        {'num': 1,  'name': 'Alice (Budget Student)',      'rooms': 1, 'roommates': 1, 'budget':  8000, 'months': 12},
        {'num': 2,  'name': 'Bob (Shared Apartment)',       'rooms': 2, 'roommates': 2, 'budget': 12000, 'months':  6},
        {'num': 3,  'name': 'Charlie (Luxury Seeker)',      'rooms': 4, 'roommates': 2, 'budget': 60000, 'months': 12},
        {'num': 4,  'name': 'Dave (Professional)',          'rooms': 2, 'roommates': 1, 'budget': 15000, 'months':  9},
        {'num': 5,  'name': 'Eve (Solo Living)',            'rooms': 1, 'roommates': 0, 'budget': 11000, 'months': 24},
        {'num': 6,  'name': 'Frank (Budget Conscious)',     'rooms': 1, 'roommates': 1, 'budget':  9000, 'months': 12},
        {'num': 7,  'name': 'Grace (Short Term)',           'rooms': 2, 'roommates': 1, 'budget': 14000, 'months':  3},
        {'num': 8,  'name': 'Henry (Family Space)',         'rooms': 3, 'roommates': 3, 'budget': 25000, 'months': 18},
        {'num': 9,  'name': 'Irene (Long Term Saver)',      'rooms': 1, 'roommates': 0, 'budget':  7000, 'months': 36},
        {'num': 10, 'name': 'Jack (Flexible)',              'rooms': 2, 'roommates': 2, 'budget': 13000, 'months':  9},
        {'num': 11, 'name': 'Kate (High Budget Solo)',      'rooms': 2, 'roommates': 0, 'budget': 25000, 'months': 12},
        {'num': 12, 'name': 'Liam (Short Stay)',            'rooms': 1, 'roommates': 1, 'budget':  9000, 'months':  3},
        {'num': 13, 'name': 'Mia (Big Group Seeker)',       'rooms': 4, 'roommates': 5, 'budget': 30000, 'months': 12},
        {'num': 14, 'name': 'Noah (Family Style)',          'rooms': 3, 'roommates': 3, 'budget': 28000, 'months': 18},
        {'num': 15, 'name': 'Olivia (Remote Worker)',       'rooms': 2, 'roommates': 1, 'budget': 16000, 'months': 12},
        {'num': 16, 'name': 'Paul (Frugal)',                'rooms': 1, 'roommates': 2, 'budget':  6000, 'months':  6},
        {'num': 17, 'name': 'Quinn (Premium Long Term)',    'rooms': 3, 'roommates': 2, 'budget': 45000, 'months': 24},
        {'num': 18, 'name': 'Rose (Minimalist)',            'rooms': 1, 'roommates': 0, 'budget':  5000, 'months':  6},
        {'num': 19, 'name': 'Sam (Social Butterfly)',       'rooms': 2, 'roommates': 4, 'budget': 14000, 'months': 12},
        {'num': 20, 'name': 'Tina (Midrange Short)',        'rooms': 2, 'roommates': 1, 'budget': 12000, 'months':  4},
        {'num': 21, 'name': 'Uma (Spacious)',               'rooms': 3, 'roommates': 1, 'budget': 22000, 'months': 12},
        {'num': 22, 'name': 'Victor (Large Group)',         'rooms': 4, 'roommates': 4, 'budget': 35000, 'months': 10},
        {'num': 23, 'name': 'Wendy (Two Roommates)',        'rooms': 2, 'roommates': 2, 'budget': 15000, 'months':  8},
        {'num': 24, 'name': 'Xavier (High End)',            'rooms': 4, 'roommates': 1, 'budget': 60000, 'months': 18},
        {'num': 25, 'name': 'Yara (Economical Long)',       'rooms': 1, 'roommates': 2, 'budget':  8000, 'months': 24},
        {'num': 26, 'name': 'Zack (Max Roommates)',         'rooms': 3, 'roommates': 5, 'budget': 20000, 'months': 12},
        {'num': 27, 'name': 'Anna (Starter)',               'rooms': 1, 'roommates': 1, 'budget':  7000, 'months':  6},
        {'num': 28, 'name': 'Ben (Work Travel)',            'rooms': 1, 'roommates': 3, 'budget': 10000, 'months':  5},
        {'num': 29, 'name': 'Cara (Calm)',                  'rooms': 2, 'roommates': 0, 'budget': 11000, 'months': 12},
        {'num': 30, 'name': 'Dan (Music)',                  'rooms': 2, 'roommates': 3, 'budget': 13000, 'months': 11},
        {'num': 31, 'name': 'Ella (Graduate)',              'rooms': 1, 'roommates': 2, 'budget':  9000, 'months': 10},
        {'num': 32, 'name': 'Finn (Long Lease)',            'rooms': 2, 'roommates': 1, 'budget': 12500, 'months': 24},
        {'num': 33, 'name': 'Gia (Family Sized)',           'rooms': 4, 'roommates': 3, 'budget': 40000, 'months': 24},
        {'num': 34, 'name': 'Hugo (Big Budget Group)',      'rooms': 3, 'roommates': 4, 'budget': 50000, 'months': 12},
        {'num': 35, 'name': 'Ivy (Compact Duo)',            'rooms': 1, 'roommates': 1, 'budget':  8500, 'months':  9},
    ]
    
    # Generate random UUIDs and create user dictionary with id
    users = []
    for user_data in users_data:
        user_id = str(uuid.uuid4())
        user = {
            'id': user_id,
            'name': user_data['name'],
            'rooms': user_data['rooms'],
            'roommates': user_data['roommates'],
            'budget': user_data['budget'],
            'months': user_data['months']
        }
        users.append(user)
    
    # Store mapping for setup_sample_groups to use
    global _SAMPLE_USER_IDS
    _SAMPLE_USER_IDS = {i+1: user['id'] for i, user in enumerate(users)}
    
    return users

# Global to store sample user ID mapping
_SAMPLE_USER_IDS = {}


def create_user_interactive() -> Optional[Dict]:
    """
    Interactive user creation using questionary prompts.
    
    Generates a UUID (Universally Unique Identifier) for the user.
    UUID format: 8-4-4-4-12 hexadecimal characters (e.g., "550e8400-e29b-41d4-a716-446655440000")
    
    Returns:
        dict: User data with preferences, or None if cancelled
    """
    try:
        # Generate a new UUID
        default_uuid = str(uuid.uuid4())
        
        print("\n💡 UUID Info: A universally unique identifier in format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")
        print(f"   Generated UUID for you: {default_uuid}")
        print("   (UUID ensures no ID conflicts in the system)")
        
        user_id = questionary.text(
            "Enter user ID (UUID format recommended, press Enter to use generated one):",
            default=default_uuid
        ).ask()

        if not user_id:
            return None
        
        # Validate UUID format (with warning if not UUID, but allow it)
        try:
            uuid.UUID(user_id)  # This will raise ValueError if invalid
        except ValueError:
            print("⚠️  Warning: Not a standard UUID format. This may cause ID conflicts.")
            confirm = questionary.confirm(
                "Continue with this ID anyway?",
                default=False
            ).ask()
            if not confirm:
                return None

        name = questionary.text(
            "Enter name:",
            default="New User"
        ).ask()

        rooms = questionary.text(
            "How many rooms do you need? (1-4):",
            default="2",
            validate=lambda x: x.isdigit() and 1 <= int(x) <= 4
        ).ask()

        roommates = questionary.text(
            "How many roommates do you want? (0-5):",
            default="1",
            validate=lambda x: x.isdigit() and 0 <= int(x) <= 5
        ).ask()

        budget = questionary.text(
            "Monthly budget (rubles):",
            default="15000",
            validate=lambda x: x.isdigit() and int(x) > 0
        ).ask()

        months = questionary.text(
            "Rental period (months):",
            default="12",
            validate=lambda x: x.isdigit() and int(x) > 0
        ).ask()

        user_data = {
            'id': user_id,
            'name': name,
            'rooms': int(rooms),
            'roommates': int(roommates),
            'budget': int(budget),
            'months': int(months)
        }

        return user_data

    except (KeyboardInterrupt, TypeError):
        return None


def get_all_user_ids(session) -> List[tuple]:
    """
    Get list of all user IDs and names from database.
    
    Args:
        session: Neo4j session
        
    Returns:
        list: List of tuples (user_id, name)
    """
    query = "MATCH (u:User) RETURN u.id as id, u.name as name ORDER BY u.id"
    result = session.run(query)
    return [(record['id'], record['name'] or record['id']) for record in result]


def repair_users_without_groups(session, caps: dict, use_weights: bool, weights: dict):
    """
    Find and repair any users who don't have a group (should never happen, but safety net).
    
    Args:
        session: Neo4j session
        caps: Normalization caps
        use_weights: Whether to use weighted vectors
        weights: Parameter weights
        
    Returns:
        int: Number of users repaired
    """
    from infrastructure.neo4j.user_ops import get_user_parameters
    from recommendation import create_vector
    from infrastructure.config import get_parameter_statistics, GROUP_PARAMETER_WEIGHTS
    from infrastructure.config import PARAMETERS
    
    # Find users without groups
    query = """
        MATCH (u:User)
        WHERE NOT (u)-[:MEMBER_OF]->(:Group)
        RETURN u.id as user_id, u.name as name
    """
    result = session.run(query)
    users_without_groups = [record for record in result]
    
    if not users_without_groups:
        return 0
    
    print(f'⚠️  Found {len(users_without_groups)} user(s) without groups. Repairing...')
    
    weights = weights or GROUP_PARAMETER_WEIGHTS
    repaired = 0
    
    for user_record in users_without_groups:
        user_id = user_record['user_id']
        try:
            # Get user parameters
            user_params = get_user_parameters(session, user_id)
            
            # Create single-member group
            group_id = user_id
            group_name = f"Group of {user_record['name'] or user_id}"
            
            # Create vector
            group_vector = create_vector(
                user_params, 
                PARAMETERS, 
                statistics=get_parameter_statistics(),
                weights=weights if use_weights else None
            )
            
            # Create group and link user
            repair_query = """
                MATCH (u:User {id: $user_id})
                MERGE (g:Group {id: $group_id})
                SET g.name = $group_name,
                    g.rooms = $rooms,
                    g.roommates = $roommates,
                    g.budget = $budget,
                    g.months = $months,
                    g.embedding = $embedding
                MERGE (u)-[:MEMBER_OF]->(g)
                WITH g
                UNWIND $param_list AS param
                MERGE (gp:GroupParameter {groupId: $group_id, name: param.name})
                SET gp.value = param.value
                MERGE (g)-[:HAS_PARAMETER]->(gp)
            """
            
            parameters_list = [
                {'name': p, 'value': user_params.get(p, 0)} for p in PARAMETERS
            ]
            
            session.run(
                repair_query,
                user_id=user_id,
                group_id=group_id,
                group_name=group_name,
                rooms=user_params.get('rooms', 0),
                roommates=user_params.get('roommates', 0),
                budget=user_params.get('budget', 0),
                months=user_params.get('months', 0),
                embedding=group_vector,
                param_list=parameters_list,
            )
            
            print(f'  ✓ Repaired user {user_id} - created group {group_id}')
            repaired += 1
            
        except Exception as e:
            print(f'  ✗ Failed to repair user {user_id}: {e}')
    
    return repaired


def setup_sample_groups(session, caps: dict, use_weights: bool, weights: dict):
    """
    Group sample users into predefined groups for realistic testing.
    
    Creates 6-8 groups with 2-5 members each from existing users.
    Call this after upsert_users() to organize users into groups.
    Uses the UUID mapping created by sample_users().
    
    Args:
        session: Neo4j session
        caps: Normalization caps
        use_weights: Whether to use weighted vectors
        weights: Parameter weights
    """
    from infrastructure.neo4j.group_ops import add_user_to_group

    # Define group assignments using user numbers (will be mapped to UUIDs)
    # (owner_num is group owner, member_nums join that group)
    group_configs = [
        {'owner': 1, 'members': [6, 27]},  # Budget students group
        {'owner': 2, 'members': [10, 23]},  # Shared apartment seekers
        {'owner': 3, 'members': [24]},  # Luxury seekers
        {'owner': 4, 'members': [15, 32]},  # Professionals group
        {'owner': 8, 'members': [14, 21]},  # Family-sized group
        {'owner': 13, 'members': [19, 26, 34]},  # Big group seekers
        {'owner': 17, 'members': [33]},  # Premium long-term
        # Other users remain in single-person groups: 5, 7, 9, 11, 12, 16, 18, 20, 22, 25, 28, 29, 30, 31, 35
    ]

    # Map user numbers to UUIDs
    if not _SAMPLE_USER_IDS:
        print("⚠️  Warning: Sample user IDs not found. Skipping group setup.")
        return

    # All users should always have a group - no deletion of groups

    # Execute groupings
    for config in group_configs:
        owner_uuid = _SAMPLE_USER_IDS.get(config['owner'])
        if not owner_uuid:
            continue
            
        target_group_id = owner_uuid
        for member_num in config['members']:
            member_uuid = _SAMPLE_USER_IDS.get(member_num)
            if member_uuid:
                add_user_to_group(
                    session,
                    member_uuid,
                    target_group_id,
                    caps=caps,
                    use_weights=use_weights,
                    weights=weights
                )


def auto_group_users(session, users: List[Dict], caps: dict, use_weights: bool, weights: dict, group_probability: float = 0.4, leave_some_solo: float = 0.2):
    """
    Automatically group generated users with some probability.
    Respects group size constraints based on user's desired roommates count.
    
    Args:
        session: Neo4j session
        users: List of user dictionaries
        caps: Normalization caps
        use_weights: Whether to use weighted vectors
        weights: Parameter weights
        group_probability: Chance of creating a group (default 0.4)
        leave_some_solo: Fraction of users to leave in single-person groups (default 0.2, i.e., 20%)
        
    Note:
        All users will always have a group node. Some will be in single-person groups.
        Group size is limited by min(owner_desired_roommates + 1, DEFAULT_MAX_ROOMMATES + 1)
    """
    from infrastructure.neo4j.group_ops import add_user_to_group

    # Sort users by similarity (simple heuristic)
    sorted_users = sorted(users, key=lambda u: (u['rooms'], u['budget']))

    # All users should remain in groups - no "truly solo" users without groups
    # We'll leave some users in single-person groups based on leave_some_solo probability
    
    i = 0
    while i < len(sorted_users):
        # Random chance to create a group (if we're not leaving this user solo)
        if random.random() < group_probability and i + 1 < len(sorted_users):
            # Calculate max group size based on owner's roommates preference
            owner = sorted_users[i]
            owner_desired_roommates = owner.get('roommates', 1)
            
            # Max group size = min(desired_roommates + 1, DEFAULT_MAX_ROOMMATES + 1)
            # Import DEFAULT_MAX_ROOMMATES from config
            from infrastructure.config import DEFAULT_MAX_ROOMMATES
            max_group_size = min(
                int(owner_desired_roommates) + 1,  # +1 to include the owner
                DEFAULT_MAX_ROOMMATES + 1,
                len(sorted_users) - i  # Can't exceed remaining users
            )
            
            # Create group with 2 to max_group_size members
            if max_group_size >= 2:
                group_size = min(random.randint(2, max_group_size), len(sorted_users) - i)
                members = sorted_users[i+1:i+group_size]

                if members:  # Only create group if there are valid members
                    target_group_id = owner['id']
                    for member in members:
                        try:
                            add_user_to_group(
                                session,
                                member['id'],
                                target_group_id,
                                caps=caps,
                                use_weights=use_weights,
                                weights=weights
                            )
                        except Exception:
                            pass  # Skip if grouping fails

                i += group_size
            else:
                # Owner doesn't want roommates, leave in single-person group
                i += 1
        else:
            # Leave user in single-person group
            i += 1

