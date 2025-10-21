# Interactive Roommate Matching Simulation

## Overview

This simulation allows you to experience the roommate matching system interactively. The system generates fake users, lets you create your own profile, find similar groups, and join/leave groups.

## How to Run

```bash
cd repository/recommendation_system
python simulation.py
```

## What Happens

1. **Database Setup**: The system sets up the Neo4j database with constraints and indexes
2. **Generate Fake Users**: Creates 20 fake users with random preferences (rooms, roommates, budget, months)
3. **User Registration**: You'll be prompted to enter your preferences:
   - User ID (or auto-generated)
   - Name
   - Number of rooms needed (1-4)
   - Number of roommates wanted (0-5)
   - Monthly budget (in rubles)
   - Rental duration (in months)
4. **Find Similar Groups**: The system finds up to 10 groups that match your preferences
5. **Display Recommendations**: Shows recommended groups with match percentage, preferences, and current members
6. **Join a Group**: You can choose which group to join (1-10) or skip (0)
7. **Leave Group**: If you joined a group, you'll be asked if you want to leave (y/n)

## Functions Available

### `generate_fake_users(count)`
Generates `count` number of fake users with random but realistic preferences.

```python
fake_users = generate_fake_users(30)
```

### `create_form()`
Interactive form that prompts user for their roommate preferences.

```python
user_data = create_form()
# Returns: {'id': 'user123', 'name': 'John', 'rooms': 2, 'roommates': 1, 'budget': 15000, 'months': 12}
```

### `get_similar_groups(session, user_data, top_k=5)`
Finds similar groups for a user based on their preferences.

```python
recommendations = get_similar_groups(session, user_data, top_k=10)
```

### `run_interactive_simulation(fake_user_count=20)`
Runs the complete interactive simulation workflow.

## Advanced Usage

You can use the individual functions for custom workflows:

```python
from simulation import (
    generate_fake_users,
    create_form,
    get_similar_groups,
    join_group_interactive,
    leave_group_interactive
)
from db_management_utils import get_driver, ensure_constraints_and_index, upsert_users, PARAMETERS

# Custom simulation
with get_driver() as driver:
    with driver.session() as session:
        # Setup
        ensure_constraints_and_index(session, dims=len(PARAMETERS))
        
        # Generate and insert fake users
        fake_users = generate_fake_users(50)
        upsert_users(session, fake_users)
        
        # User creates profile
        user = create_form()
        upsert_users(session, [user])
        
        # Find and display recommendations
        recommendations = get_similar_groups(session, user, top_k=10)
        
        # Join a group
        joined_group = join_group_interactive(session, user['id'], recommendations)
        
        # Leave group if desired
        if joined_group:
            leave_group_interactive(session, user['id'])
```

## Other Simulation Functions

### `sample_users()`
Returns a predefined list of 35 diverse test users for consistent testing.

### `simulate_group_formation(session, max_iterations=10, max_roommates_per_group=4)`
Automatically simulates group formation by having users randomly join compatible groups.

```python
with get_driver() as driver:
    with driver.session() as session:
        ensure_constraints_and_index(session, dims=len(PARAMETERS))
        users = sample_users()
        upsert_users(session, users)
        
        # Run automated simulation
        results = simulate_group_formation(
            session,
            max_iterations=15,
            max_roommates_per_group=5,
            use_weights=True,
            verbose=True
        )
        
        print(f"Successful joins: {results['successful_joins']}")
        print(f"Final groups: {results['final_groups']}")
```

## Requirements

- Neo4j database running locally
- `.env` file with Neo4j credentials:
  ```
  NEO4J_URI=bolt://localhost:7687
  NEO4J_USERNAME=neo4j
  NEO4J_PASSWORD=your_password
  ```
- Python packages: `neo4j`, `python-dotenv`

## Notes

- The simulation uses cosine similarity to match users with similar preferences
- Groups maintain average preferences of all members
- When you join a group, your old single-member group is deleted
- When you leave a group, a new single-member group is created for you

