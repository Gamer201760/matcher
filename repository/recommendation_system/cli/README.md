# Interactive Roommate Matcher CLI

A beautiful, interactive command-line interface for the Roommate Matching System built with `questionary` and `rich`.

## Features

- 🔍 **Get Recommendations** - Find matching groups based on your preferences
- 🤝 **Join Groups** - Join recommended groups with a single selection
- 🚪 **Leave Groups** - Leave your current group and create a new one
- 👁️ **View Groups** - See detailed information about your group or all groups
- 🌳 **Tree View** - Visualize all groups in a beautiful tree structure (like Linux `tree`)
- 👤 **Switch Users** - Test different user perspectives
- 📊 **Statistics** - View database statistics
- ➕ **Add Users** - Generate random or sample users for testing
- 🔧 **Rebuild Indexes** - Rebuild vector indexes (if recommendations fail)
- 🧹 **Clean Database** - Reset the database

## Installation

Dependencies are listed in `requirements.txt`:
```bash
pip install -r requirements.txt
```

Or install manually:
```bash
pip install questionary rich neo4j python-dotenv
```

## Usage

### Recommended: Use the convenience script from project root
```bash
# Make sure you're in the virtual environment first
.\.venv\Scripts\Activate.ps1  # Windows
# or
source .venv/bin/activate      # Linux/Mac

# Then run the CLI
python run_cli.py
```

### Alternative: Run as module
```bash
python -m repository.recommendation_system.cli.main
```

### Alternative: Run directly
```bash
python repository/recommendation_system/cli/main.py
```

**Note**: Always activate your virtual environment first to ensure all dependencies are available.

## Menu Navigation

The CLI uses interactive menus with keyboard navigation:
- **↑/↓ arrows**: Navigate options
- **Enter**: Select option
- **Ctrl+C**: Cancel current operation

## Workflow Example

1. **Start** → Choose to clean DB or keep existing data
2. **Setup** → Create new user, select existing, or generate samples
3. **Main Menu** → Navigate using arrow keys
4. **Get Recommendations** → See top matching groups
5. **Join Group** → Select from recommendations
6. **View Group** → See your current group details
7. **Tree View** → Visualize all groups and members

## Display Features

### Recommendations Table
Shows match percentage, group ID, member count, and average parameters.

### Group Tree View
```
Groups/ (15 total)
├── g_user1 (2 members) — rooms: 2, roommates: 1, budget: ₽15000/mo, months: 12
│   ├── Alice (user1)
│   └── Bob (user2)
└── g_user3 (1 member) — rooms: 1, roommates: 0, budget: ₽8000/mo, months: 6
    └── Charlie (user3)
```

### Statistics Panel
- Total users and groups
- Average, min, and max group sizes
- Color-coded metrics

## Architecture

```
cli/
├── __init__.py      # Package exports
├── main.py          # Entry point
├── menus.py         # Menu loops
├── actions.py       # Action handlers
├── displays.py      # Rich displays
└── utils.py         # Helper functions
```

## Development

### Adding New Actions

1. Add action handler in `actions.py`
2. Add menu item in `menus.py`
3. Add display function in `displays.py` (if needed)

### Customization

- **Colors**: Modify color codes in `displays.py`
- **Caps**: Adjust normalization caps in `main.py`
- **Weights**: Configure parameter weights via `group_parameter_weights`

## Testing

Run CLI function tests to verify all displays work correctly:

```bash
python tests/test_cli_functions.py
```

Or run all tests:

```bash
python tests/run_tests.py tests.test_cli_functions
```

These tests verify:
- All display functions render without errors
- Utility functions generate valid data
- Sample users are properly grouped
- Database queries work correctly

## Troubleshooting

**Import errors**: Make sure you're running from the correct directory and the parent packages are in Python path.

**Neo4j connection**: Ensure Neo4j is running and `.env` is configured with correct credentials.

**Dependencies**: Run `pip install -r requirements.txt` to install all required packages.

**"No such vector schema index" error**: If recommendations fail with `group_vec_index` not found:
1. Use the "🔧 Rebuild Indexes" option from the main menu, OR
2. Clean the database and restart the CLI (indexes are auto-created on startup)

**All groups have single members**: If sample users aren't grouped:
1. Clean the database using "🧹 Clean Database"
2. Select "Generate sample users first" from the startup menu
3. The system will now automatically organize users into 7 multi-member groups

