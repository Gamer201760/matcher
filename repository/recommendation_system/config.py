"""
Configuration file for the Roommate Recommendation System.

This module contains all constant parameters, weights, and settings
used throughout the recommendation system and CLI.
"""
import math

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
    'months': 64       # Maximum rental duration in months
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
    'budget': 1,
    'months': 1
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
# CLI DISPLAY SETTINGS
# ============================================================================

# Rounding mode for display values (options: 'ceil', 'floor', 'round', None for no rounding)
# Only affects display, not calculations
DISPLAY_ROUNDING_MODE = 'ceil'

# Number of decimal places for budget display
BUDGET_DECIMAL_PLACES = 0

# Number of decimal places for other numeric displays
NUMERIC_DECIMAL_PLACES = 1

# Maximum number of groups to show in tree view by default
DEFAULT_TREE_MAX_GROUPS = 50

# Default number of recommendations to show
DEFAULT_RECOMMENDATION_COUNT = 10

# ============================================================================
# CLI USER GENERATION SETTINGS
# ============================================================================

# Default number of sample users to generate at startup
DEFAULT_SAMPLE_USER_COUNT = 35

# Budget range for generated fake users (min, max)
FAKE_USER_BUDGET_RANGE = (5000, 60000)

# Possible months values for generated fake users
FAKE_USER_MONTHS_OPTIONS = [3, 6, 9, 12, 18, 24, 36]

# Rooms range for generated users (min, max)
FAKE_USER_ROOMS_RANGE = (1, 4)

# Roommates range for generated users (min, max)
FAKE_USER_ROOMMATES_RANGE = (1, 5)

# Probability of auto-grouping generated users
AUTO_GROUP_PROBABILITY = 0.4

# ============================================================================
# NORMALIZATION WEIGHTS (DYNAMIC CALCULATION)
# ============================================================================

# Import the normalization weight calculator
from .calculate_normalization_weights import calculate_optimal_normalization_weights

# Calculate normalization weights dynamically on import
# These weights equalize parameter distributions before importance weights are applied
# 
# Two-stage weighting system:
# 1. NORMALIZATION_WEIGHTS: Correct for different typical ranges vs caps (this section)
#    - Ensures all parameters have similar mean values after normalization
#    - Example: 'budget' typically uses 16% of cap, 'months' uses 42% of cap
#    - Without these weights, parameters would be biased before importance weighting
#
# 2. GROUP_PARAMETER_WEIGHTS: Express matching priorities (defined above)
#    - Applied after normalization to prioritize important parameters
#    - Example: rooms (8.0) is more important than months (1.2)
#
# The calculation uses scipy optimization to minimize variance of parameter means,
# ensuring fair comparison before importance weights are applied.
# Typically takes <1 second on startup.
#
# See normalization_weights.ipynb for detailed analysis and visualization.

NORMALIZATION_WEIGHTS = calculate_optimal_normalization_weights(
    sample_size=1000,
    parameters=PARAMETERS,
    default_caps=DEFAULT_CAPS,
    user_ranges={
        'rooms': FAKE_USER_ROOMS_RANGE,
        'roommates': FAKE_USER_ROOMMATES_RANGE,
        'budget': FAKE_USER_BUDGET_RANGE,
        'months': FAKE_USER_MONTHS_OPTIONS
    }
)

# ============================================================================
# LOGGING SETTINGS
# ============================================================================

# Default log level for all modules
DEFAULT_LOG_LEVEL = 'INFO'

# Log levels for specific modules (optional overrides)
MODULE_LOG_LEVELS = {
    'cli': 'INFO',
    'roommate_db': 'INFO',
    'test_service': 'INFO'
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def round_for_display(value: float, is_budget: bool = False) -> float:
    """
    Round numeric values for display based on configured rounding mode.
    
    Args:
        value: The value to round
        is_budget: Whether this is a budget value (uses different decimal places)
    
    Returns:
        Rounded value according to DISPLAY_ROUNDING_MODE setting
    """
    if value is None or DISPLAY_ROUNDING_MODE is None:
        return value
    
    decimal_places = BUDGET_DECIMAL_PLACES if is_budget else NUMERIC_DECIMAL_PLACES
    multiplier = 10 ** decimal_places
    
    if DISPLAY_ROUNDING_MODE == 'ceil':
        return math.ceil(value * multiplier) / multiplier
    elif DISPLAY_ROUNDING_MODE == 'floor':
        return math.floor(value * multiplier) / multiplier
    elif DISPLAY_ROUNDING_MODE == 'round':
        return round(value, decimal_places)
    else:
        return value

