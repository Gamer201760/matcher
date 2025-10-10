# simulation.py
"""Interactive roommate matching simulation"""
import random
from db_management_utils import (
    get_driver,
    ensure_constraints_and_index,
    upsert_users,
    find_similar,
    add_user_to_group,
    remove_user_from_group,
    get_group_info,
    get_user_parameters,
    get_group_member_parameters,
    clean_db,
    PARAMETERS
)
from user_vector_utils import (
    create_user_vector,
    create_group_vector_with_weights,
    group_parameter_weights,
)
from logging_utils import setup_logger, log_vector_operation, log_similarity_results
import dotenv
dotenv.load_dotenv()

# Setup logger
logger = setup_logger("simulation", "INFO")


def generate_fake_users(count):
    """Generate random users with realistic preferences for simulation.
    
    Args:
        count: Number of fake users to generate
        
    Returns:
        list: List of user dictionaries with random preferences
    """
    names = [
        'Alex', 'Bailey', 'Cameron', 'Dakota', 'Eden', 'Finley', 'Gray', 'Harper',
        'Iris', 'Jordan', 'Kennedy', 'Logan', 'Morgan', 'Nico', 'Oakley', 'Parker',
        'Quinn', 'Riley', 'Sage', 'Taylor', 'Uma', 'Val', 'Winter', 'Xen', 'Yuki',
        'Zara', 'Andy', 'Blake', 'Casey', 'Drew', 'Ellis', 'Frankie', 'Gene', 'Hayden'
    ]
    
    users = []
    for i in range(count):
        user_id = f'sim_u{i+1}'
        name = random.choice(names) if i < len(names) else f'User{i+1}'
        
        users.append({
            'id': user_id,
            'name': name,
            'rooms': random.randint(1, 4),
            'roommates': random.randint(0, 5),
            'budget': random.randint(5000, 60000),
            'months': random.choice([3, 6, 9, 12, 18, 24, 36])
        })
    
    logger.info(f"✓ Generated {count} fake users")
    return users


def create_form():
    """Interactive form to collect user preferences.
    
    Returns:
        dict: User data with preferences
    """
    print("\n" + "="*60)
    print("🏠 ROOMMATE MATCHING - USER REGISTRATION")
    print("="*60)
    
    try:
        user_id = input("\nEnter your user ID (e.g., 'user123'): ").strip()
        if not user_id:
            user_id = f'user_{random.randint(1000, 9999)}'
            print(f"  → Generated ID: {user_id}")
        
        name = input("Enter your name: ").strip()
        if not name:
            name = f"User {user_id}"
            print(f"  → Using default name: {name}")
        
        rooms = int(input("How many rooms do you need? (1-4): ").strip() or 2)
        roommates = int(input("How many roommates do you want? (0-5): ").strip() or 1)
        budget = int(input("What's your monthly budget? (in rubles): ").strip() or 15000)
        months = int(input("How many months do you want to rent? (e.g., 12): ").strip() or 12)
        
        user_data = {
            'id': user_id,
            'name': name,
            'rooms': rooms,
            'roommates': roommates,
            'budget': budget,
            'months': months
        }
        
        print("\n✓ Registration complete!")
        print(f"  ID: {user_id}")
        print(f"  Name: {name}")
        print(f"  Preferences: {rooms} rooms, {roommates} roommates, ₽{budget}/mo, {months} months")
        
        return user_data
        
    except (ValueError, KeyboardInterrupt) as e:
        print(f"\n❌ Error during registration: {e}")
        return None


def get_similar_groups(session, user_data, top_k=5, caps=None, use_weights=True, weights=None):
    """Find similar groups for a user.
    
    Args:
        session: Neo4j session
        user_data: User dictionary with preferences
        top_k: Number of recommendations
        caps: Normalization caps
        use_weights: Whether to use weighted vectors
        weights: Parameter weights
        
    Returns:
        list: List of similar group dictionaries
    """
    caps = caps or {'budget': 200000, 'months': 36}
    weights = weights or group_parameter_weights
    
    # Create query vector
    group_values = {p: user_data.get(p, 0) for p in PARAMETERS}
    if use_weights:
        query_vec = create_group_vector_with_weights(group_values, PARAMETERS, weights, caps)
    else:
        query_vec = create_user_vector(group_values, PARAMETERS, caps)
    
    # Find similar groups (exclude user's own group if they have one)
    exclude_id = f"g_{user_data['id']}"
    results = find_similar(session, query_vec, top_k=top_k, exclude_id=exclude_id)
    
    logger.info(f"Found {len(results)} similar groups for user {user_data['id']}")
    return results


def display_group_recommendations(session, recommendations):
    """Display group recommendations with details.
    
    Args:
        session: Neo4j session
        recommendations: List of group recommendation dictionaries
    """
    print("\n" + "="*60)
    print("💫 RECOMMENDED GROUPS FOR YOU")
    print("="*60)
    
    if not recommendations:
        print("\n❌ No recommendations found.")
        return
    
    for i, rec in enumerate(recommendations, 1):
        group_id = rec['id']
        group_info = get_group_info(session, group_id)
        
        if group_info:
            # Get actual member averages for accurate display
            member_params = get_group_member_parameters(session, group_id)
            
            if member_params:
                # Calculate actual averages from members
                actual_params = {}
                from db_management_utils import PARAMETERS
                for param in PARAMETERS:
                    values = [m[param] for m in member_params if param in m]
                    if values:
                        actual_params[param] = sum(values) / len(values)
            else:
                # Fallback to GroupParameter values
                actual_params = group_info['parameters']
            
            members = group_info['members']
            match_pct = rec['score'] * 100
            
            print(f"\n{i}. {rec['name']} (ID: {group_id})")
            print(f"   Match: {match_pct:.1f}%")
            print(f"   Preferences: {actual_params.get('rooms', 0):.1f} rooms, "
                  f"{actual_params.get('roommates', 0):.1f} roommates, "
                  f"₽{actual_params.get('budget', 0):.0f}/mo, "
                  f"{actual_params.get('months', 0):.1f} months")
            print(f"   Members ({len(members)}): {', '.join([m['name'] or m['id'] for m in members])}")


def join_group_interactive(session, user_id, recommendations, caps=None, use_weights=True, weights=None):
    """Let user choose and join a group interactively.
    
    Args:
        session: Neo4j session
        user_id: User ID
        recommendations: List of group recommendations
        caps: Normalization caps
        use_weights: Whether to use weighted vectors
        weights: Parameter weights
        
    Returns:
        str: Joined group ID or None
    """
    if not recommendations:
        print("\n❌ No groups available to join.")
        return None
    
    print("\n" + "-"*60)
    try:
        choice = input(f"\nWhich group would you like to join? (1-{len(recommendations)}, or 0 to skip): ").strip()
        
        if not choice or choice == '0':
            print("⚠️  Skipping group join.")
            return None
        
        choice_idx = int(choice) - 1
        if 0 <= choice_idx < len(recommendations):
            target_group = recommendations[choice_idx]
            target_group_id = target_group['id']
            
            print(f"\n🔄 Joining group {target_group['name']}...")
            
            success = add_user_to_group(
                session, 
                user_id, 
                target_group_id, 
                caps=caps, 
                use_weights=use_weights, 
                weights=weights
            )
            
            if success:
                print(f"✅ Successfully joined group {target_group_id}!")
                
                # Show updated group info with actual member averages
                group_info = get_group_info(session, target_group_id)
                if group_info:
                    print(f"\n📊 Updated Group Info:")
                    print(f"   Members ({len(group_info['members'])}): {', '.join([m['name'] or m['id'] for m in group_info['members']])}")
                    
                    # Calculate actual averages from members for accurate display
                    member_params = get_group_member_parameters(session, target_group_id)
                    if member_params:
                        from db_management_utils import PARAMETERS
                        actual_params = {}
                        for param in PARAMETERS:
                            values = [m[param] for m in member_params if param in m]
                            if values:
                                actual_params[param] = sum(values) / len(values)
                        
                        print(f"   New group preferences: {actual_params.get('rooms', 0):.1f} rooms, "
                              f"{actual_params.get('roommates', 0):.1f} roommates, "
                              f"₽{actual_params.get('budget', 0):.0f}/mo, "
                              f"{actual_params.get('months', 0):.1f} months")
                    else:
                        # Fallback to stored parameters
                        params = group_info['parameters']
                        print(f"   New group preferences: {params.get('rooms', 0):.1f} rooms, "
                              f"{params.get('roommates', 0):.1f} roommates, "
                              f"₽{params.get('budget', 0):.0f}/mo, "
                              f"{params.get('months', 0):.1f} months")
                
                return target_group_id
            else:
                print(f"❌ Failed to join group {target_group_id}")
                return None
        else:
            print("❌ Invalid choice.")
            return None
            
    except (ValueError, KeyboardInterrupt) as e:
        print(f"\n❌ Error: {e}")
        return None


def leave_group_interactive(session, user_id, caps=None, use_weights=True, weights=None):
    """Ask user if they want to leave their group.
    
    Args:
        session: Neo4j session
        user_id: User ID
        caps: Normalization caps
        use_weights: Whether to use weighted vectors
        weights: Parameter weights
        
    Returns:
        bool: True if left group, False otherwise
    """
    print("\n" + "-"*60)
    try:
        leave = input("\nDo you want to leave your current group? (y/n): ").strip().lower()
        
        if leave == 'y':
            print(f"\n🔄 Leaving group...")
            
            new_group_id = remove_user_from_group(
                session, 
                user_id, 
                caps=caps, 
                use_weights=use_weights, 
                weights=weights
            )
            
            if new_group_id:
                print(f"✅ Successfully left group! Created new single-member group: {new_group_id}")
                return True
            else:
                print(f"❌ Failed to leave group")
                return False
        else:
            print("⚠️  Staying in current group.")
            return False
            
    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled.")
        return False


def sample_users():
    """Generate a diverse set of test users for recommendation testing."""
    users = [
        {'id': 'u1',  'name': 'Alice (Budget Student)',      'rooms': 1, 'roommates': 1, 'budget':  8000, 'months': 12},
        {'id': 'u2',  'name': 'Bob (Shared Apartment)',       'rooms': 2, 'roommates': 2, 'budget': 12000, 'months':  6},
        {'id': 'u3',  'name': 'Charlie (Luxury Seeker)',      'rooms': 4, 'roommates': 2, 'budget': 60000, 'months': 12},
        {'id': 'u4',  'name': 'Dave (Professional)',          'rooms': 2, 'roommates': 1, 'budget': 15000, 'months':  9},
        {'id': 'u5',  'name': 'Eve (Solo Living)',            'rooms': 1, 'roommates': 0, 'budget': 11000, 'months': 24},
        {'id': 'u6',  'name': 'Frank (Budget Conscious)',     'rooms': 1, 'roommates': 1, 'budget':  9000, 'months': 12},
        {'id': 'u7',  'name': 'Grace (Short Term)',           'rooms': 2, 'roommates': 1, 'budget': 14000, 'months':  3},
        {'id': 'u8',  'name': 'Henry (Family Space)',         'rooms': 3, 'roommates': 3, 'budget': 25000, 'months': 18},
        {'id': 'u9',  'name': 'Irene (Long Term Saver)',      'rooms': 1, 'roommates': 0, 'budget':  7000, 'months': 36},
        {'id': 'u10', 'name': 'Jack (Flexible)',              'rooms': 2, 'roommates': 2, 'budget': 13000, 'months':  9},
        {'id': 'u11', 'name': 'Kate (High Budget Solo)',      'rooms': 2, 'roommates': 0, 'budget': 25000, 'months': 12},
        {'id': 'u12', 'name': 'Liam (Short Stay)',            'rooms': 1, 'roommates': 1, 'budget':  9000, 'months':  3},
        {'id': 'u13', 'name': 'Mia (Big Group Seeker)',       'rooms': 4, 'roommates': 5, 'budget': 30000, 'months': 12},
        {'id': 'u14', 'name': 'Noah (Family Style)',          'rooms': 3, 'roommates': 3, 'budget': 28000, 'months': 18},
        {'id': 'u15', 'name': 'Olivia (Remote Worker)',       'rooms': 2, 'roommates': 1, 'budget': 16000, 'months': 12},
        {'id': 'u16', 'name': 'Paul (Frugal)',                'rooms': 1, 'roommates': 2, 'budget':  6000, 'months':  6},
        {'id': 'u17', 'name': 'Quinn (Premium Long Term)',    'rooms': 3, 'roommates': 2, 'budget': 45000, 'months': 24},
        {'id': 'u18', 'name': 'Rose (Minimalist)',            'rooms': 1, 'roommates': 0, 'budget':  5000, 'months':  6},
        {'id': 'u19', 'name': 'Sam (Social Butterfly)',       'rooms': 2, 'roommates': 4, 'budget': 14000, 'months': 12},
        {'id': 'u20', 'name': 'Tina (Midrange Short)',        'rooms': 2, 'roommates': 1, 'budget': 12000, 'months':  4},
        {'id': 'u21', 'name': 'Uma (Spacious)',               'rooms': 3, 'roommates': 1, 'budget': 22000, 'months': 12},
        {'id': 'u22', 'name': 'Victor (Large Group)',         'rooms': 4, 'roommates': 4, 'budget': 35000, 'months': 10},
        {'id': 'u23', 'name': 'Wendy (Two Roommates)',        'rooms': 2, 'roommates': 2, 'budget': 15000, 'months':  8},
        {'id': 'u24', 'name': 'Xavier (High End)',            'rooms': 4, 'roommates': 1, 'budget': 60000, 'months': 18},
        {'id': 'u25', 'name': 'Yara (Economical Long)',       'rooms': 1, 'roommates': 2, 'budget':  8000, 'months': 24},
        {'id': 'u26', 'name': 'Zack (Max Roommates)',         'rooms': 3, 'roommates': 5, 'budget': 20000, 'months': 12},
        {'id': 'u27', 'name': 'Anna (Starter)',               'rooms': 1, 'roommates': 1, 'budget':  7000, 'months':  6},
        {'id': 'u28', 'name': 'Ben (Work Travel)',            'rooms': 1, 'roommates': 3, 'budget': 10000, 'months':  5},
        {'id': 'u29', 'name': 'Cara (Calm)',                  'rooms': 2, 'roommates': 0, 'budget': 11000, 'months': 12},
        {'id': 'u30', 'name': 'Dan (Music)',                  'rooms': 2, 'roommates': 3, 'budget': 13000, 'months': 11},
        {'id': 'u31', 'name': 'Ella (Graduate)',              'rooms': 1, 'roommates': 2, 'budget':  9000, 'months': 10},
        {'id': 'u32', 'name': 'Finn (Long Lease)',            'rooms': 2, 'roommates': 1, 'budget': 12500, 'months': 24},
        {'id': 'u33', 'name': 'Gia (Family Sized)',           'rooms': 4, 'roommates': 3, 'budget': 40000, 'months': 24},
        {'id': 'u34', 'name': 'Hugo (Big Budget Group)',      'rooms': 3, 'roommates': 4, 'budget': 50000, 'months': 12},
        {'id': 'u35', 'name': 'Ivy (Compact Duo)',            'rooms': 1, 'roommates': 1, 'budget':  8500, 'months':  9},
    ]
    
    logger.debug(f"Generated {len(users)} test users with diverse preferences")
    return users


def simulate_group_formation(session, max_iterations=10, max_roommates_per_group=4,
                           caps=None, use_weights=False, weights=None, verbose=True):
    """
    Simulate group formation by randomly selecting users and trying to form groups.

    Args:
        session: Neo4j session
        max_iterations: Maximum number of simulation steps
        max_roommates_per_group: Maximum members per group before stopping
        caps: Normalization caps for vector creation
        use_weights: Whether to use weighted vectors
        weights: Parameter weights for group vector creation
        verbose: Whether to log detailed information

    Returns:
        dict: Simulation results and statistics
    """
    caps = caps or {'budget': 200000, 'months': 36}
    weights = weights or group_parameter_weights

    logger.info(f"🏃 Starting group formation simulation (max {max_iterations} iterations)")
    logger.info(f"Max roommates per group: {max_roommates_per_group}")

    simulation_stats = {
        'iterations': 0,
        'successful_joins': 0,
        'failed_joins': 0,
        'groups_created': 0,
        'groups_deleted': 0,
        'group_changes': []
    }

    # Get all single-member groups (potential candidates for joining)
    single_groups_query = """
        MATCH (g:Group)
        WHERE COUNT {(g)<-[:MEMBER_OF]-()} = 1
        RETURN g.id as group_id
        ORDER BY g.id
    """
    single_groups_result = session.run(single_groups_query)
    available_groups = [record['group_id'] for record in single_groups_result]

    if verbose:
        logger.info(f"Found {len(available_groups)} single-member groups available for joining")

    for iteration in range(max_iterations):
        if not available_groups:
            if verbose:
                logger.info(f"❌ No more single-member groups available at iteration {iteration}")
            break

        # Randomly select a user to try to find a group
        selected_group_id = random.choice(available_groups)
        available_groups.remove(selected_group_id)

        # Get the user's recommendations (excluding their own group)
        user_id = selected_group_id[2:]  # Remove 'g_' prefix

        # Create query vector for this user (from Parameter nodes)
        user_record = get_user_parameters(session, user_id)
        group_values = {p: user_record[p] for p in PARAMETERS}
        if use_weights:
            query_vec = create_group_vector_with_weights(group_values, PARAMETERS, weights, caps)
        else:
            query_vec = create_user_vector(group_values, PARAMETERS, caps)

        # Find similar groups
        recommendations = find_similar(session, query_vec, top_k=5, exclude_id=selected_group_id)

        if verbose:
            logger.info(f"📊 Iteration {iteration + 1}: User {user_id} (Group {selected_group_id})")
            logger.info(f"   Looking for groups from top {len(recommendations)} recommendations")

        # Try to join the best recommendation if it's not full
        joined = False
        for rec in recommendations:
            rec_group_id = rec['id']

            # Check if target group has space
            group_info = get_group_info(session, rec_group_id)
            if not group_info:
                continue

            if group_info['member_count'] < max_roommates_per_group:
                # Try to join this group
                success = add_user_to_group(session, user_id, rec_group_id, caps, use_weights, weights)

                if success:
                    # Log the group change
                    old_group = selected_group_id
                    new_group = rec_group_id
                    new_group_info = get_group_info(session, new_group)

                    group_change = {
                        'iteration': iteration + 1,
                        'user_id': user_id,
                        'old_group': old_group,
                        'new_group': new_group,
                        'old_parameters': {p: user_record[p] for p in PARAMETERS},
                        'new_parameters': new_group_info['parameters'] if new_group_info else {},
                        'group_size': new_group_info['member_count'] if new_group_info else 0
                    }
                    simulation_stats['group_changes'].append(group_change)

                    simulation_stats['successful_joins'] += 1
                    joined = True

                    if verbose:
                        logger.info(f"   ✅ Joined group {new_group} (size: {group_change['group_size']})")
                        logger.info(f"      Old group parameters: {group_change['old_parameters']}")
                        logger.info(f"      New group parameters: {group_change['new_parameters']}")

                    break
                else:
                    simulation_stats['failed_joins'] += 1
                    if verbose:
                        logger.warning(f"   ❌ Failed to join group {rec_group_id}")
            else:
                if verbose:
                    logger.debug(f"   Skipping full group {rec_group_id} (size: {group_info['member_count']})")

        if not joined:
            if verbose:
                logger.info(f"   ⚠️  No suitable group found for user {user_id}")

        simulation_stats['iterations'] += 1

        # Update available groups list (remove any that became full)
        current_single_groups_query = """
            MATCH (g:Group)
            WHERE COUNT {(g)<-[:MEMBER_OF]-()} = 1
            RETURN g.id as group_id
        """
        current_result = session.run(current_single_groups_query)
        available_groups = [record['group_id'] for record in current_result]

    # Final statistics
    final_groups_query = "MATCH (g:Group) RETURN count(g) as total_groups"
    final_result = session.run(final_groups_query)
    final_count = final_result.single()['total_groups']

    simulation_stats['final_groups'] = final_count

    if verbose:
        logger.info("📈 Simulation completed:")
        logger.info(f"   Iterations: {simulation_stats['iterations']}")
        logger.info(f"   Successful joins: {simulation_stats['successful_joins']}")
        logger.info(f"   Failed joins: {simulation_stats['failed_joins']}")
        logger.info(f"   Final group count: {final_count}")
        logger.info(f"   Group changes logged: {len(simulation_stats['group_changes'])}")

    return simulation_stats


def run_interactive_simulation(fake_user_count=20):
    """Run the interactive roommate matching simulation.
    
    Args:
        fake_user_count: Number of fake users to generate for the database
    """
    print("\n" + "="*60)
    print("🎯 INTERACTIVE ROOMMATE MATCHING SIMULATION")
    print("="*60)
    
    # Ask if user wants to clean the database
    print("\n🗑️  Database Options")
    print("-" * 60)
    clean_choice = input("Do you want to clean the database before starting? (y/n): ").strip().lower()
    
    if clean_choice == 'y':
        print("\n🧹 Cleaning database...")
        clean_db()
        print("✓ Database cleaned successfully!")
    
    caps = {'budget': 200000, 'months': 36}
    use_weights = True
    weights = group_parameter_weights
    
    try:
        with get_driver() as driver:
            with driver.session() as session:
                # Setup database
                print("\n📦 Setting up database...")
                ensure_constraints_and_index(session, dims=len(PARAMETERS))
                
                # Generate and insert fake users
                print(f"\n👥 Generating {fake_user_count} fake users...")
                fake_users = generate_fake_users(fake_user_count)
                upsert_users(session, fake_users, caps=caps, use_weights=use_weights, weights=weights)
                print(f"✓ Inserted {len(fake_users)} users into database")
                
                # User creates their form
                user_data = create_form()
                
                if not user_data:
                    print("\n❌ Registration failed. Exiting.")
                    return
                
                # Insert user into database
                print(f"\n💾 Saving your profile to database...")
                upsert_users(session, [user_data], caps=caps, use_weights=use_weights, weights=weights)
                print("✓ Profile saved!")
                
                # Find similar groups
                print(f"\n🔍 Finding recommended groups for you...")
                recommendations = get_similar_groups(
                    session, 
                    user_data, 
                    top_k=10, 
                    caps=caps, 
                    use_weights=use_weights, 
                    weights=weights
                )
                
                # Display recommendations
                display_group_recommendations(session, recommendations)
                
                # Let user join a group
                joined_group = join_group_interactive(
                    session, 
                    user_data['id'], 
                    recommendations, 
                    caps=caps, 
                    use_weights=use_weights, 
                    weights=weights
                )
                
                # If joined, ask if they want to leave
                if joined_group:
                    leave_group_interactive(
                        session, 
                        user_data['id'], 
                        caps=caps, 
                        use_weights=use_weights, 
                        weights=weights
                    )
                
                print("\n" + "="*60)
                print("✅ SIMULATION COMPLETE")
                print("="*60)
                print("\nThank you for using the Roommate Matching System!")
                
    except Exception as e:
        logger.error(f"❌ Error during simulation: {e}")
        print(f"\n❌ Simulation error: {e}")


if __name__ == '__main__':
    # Run interactive simulation with 20 fake users
    run_interactive_simulation(fake_user_count=7)

