"""
Configuration file for the Roommate Recommendation System.

This module contains all constant parameters, weights, and settings
used throughout the recommendation system.
"""

# ============================================================================
# DATABASE PARAMETERS
# ============================================================================

# User/Group parameters used for matching
PARAMETERS = ['rooms', 'roommates', 'budget', 'months']

# Vector dimensions (must match PARAMETERS length)
VECTOR_DIMENSIONS = 4

# ============================================================================
# NORMALIZATION CAPS
# ============================================================================

# Default normalization caps for converting parameters to [0,1] range
DEFAULT_CAPS = {
    'rooms': 10,       # Maximum number of rooms
    'roommates': 10,   # Maximum number of roommates
    'budget': 200000,  # Maximum budget in rubles
    'months': 36       # Maximum rental duration in months
}

# ============================================================================
# WEIGHT CONFIGURATION
# ============================================================================

# Multiplier applied to all weights for increased sensitivity
WEIGHT_MULTIPLIER = 8

# Base weights for group parameter vectors (before multiplier)
BASE_WEIGHTS = {
    'rooms': 1.0,
    'roommates': 1.0,
    'budget': 0.35,
    'months': 0.15
}

# Final weights (base weights * multiplier)
GROUP_PARAMETER_WEIGHTS = {
    'rooms': BASE_WEIGHTS['rooms'] * WEIGHT_MULTIPLIER,
    'roommates': BASE_WEIGHTS['roommates'] * WEIGHT_MULTIPLIER,
    'budget': BASE_WEIGHTS['budget'] * WEIGHT_MULTIPLIER,
    'months': BASE_WEIGHTS['months'] * WEIGHT_MULTIPLIER
}

# ============================================================================
# SIMILARITY SEARCH SETTINGS
# ============================================================================

# Vector similarity function used in Neo4j
# Options: 'cosine' or 'euclidean'
SIMILARITY_FUNCTION = 'euclidean'

# Default number of recommendations to return
DEFAULT_TOP_K = 5

# ============================================================================
# GROUP MANAGEMENT SETTINGS
# ============================================================================

# Maximum number of roommates allowed in a group
DEFAULT_MAX_ROOMMATES = 4

# Whether groups become inactive when reaching max capacity
AUTO_DEACTIVATE_FULL_GROUPS = True

# ============================================================================
# SIMULATION SETTINGS
# ============================================================================

# Default number of fake users to generate in simulation
DEFAULT_FAKE_USER_COUNT = 20

# Default number of simulation iterations
DEFAULT_SIMULATION_ITERATIONS = 15

# Budget range for generated fake users (min, max)
FAKE_USER_BUDGET_RANGE = (5000, 60000)

# Possible months values for generated fake users
FAKE_USER_MONTHS_OPTIONS = [3, 6, 9, 12, 18, 24, 36]

# ============================================================================
# LOGGING SETTINGS
# ============================================================================

# Default log level for all modules
DEFAULT_LOG_LEVEL = 'INFO'

# Log levels for specific modules (optional overrides)
MODULE_LOG_LEVELS = {
    'simulation': 'INFO',
    'roommate_db': 'INFO',
    'test_service': 'INFO'
}

