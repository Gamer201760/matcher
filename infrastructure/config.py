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
# NORMALIZATION CONFIGURATION
# ============================================================================

# Normalization method: 'ZSCORE' or 'PERCENTILE'
NORMALIZATION_METHOD = 'ZSCORE'

# Parameter statistics (structure depends on normalization method)
# Updated dynamically by calling update_statistics() after user generation
PARAMETER_STATISTICS = {
    'rooms': {'mean': 2.5, 'std': 1.0},
    'roommates': {'mean': 3.0, 'std': 1.5},
    'budget': {'mean': 30000, 'std': 20000},
    'months': {'mean': 12, 'std': 8},
}


def get_normalizer():
    """
    Get the configured normalization strategy instance.
    
    Returns:
        NormalizationStrategy: Instance of the configured normalizer
    
    Raises:
        ValueError: If NORMALIZATION_METHOD is unknown
    """
    from recommendation.ZSCORE_NORMALIZATION import ZScoreNormalization
    from recommendation.PERCENTILE_NORMALIZATION import PercentileNormalization
    
    if NORMALIZATION_METHOD == 'ZSCORE':
        return ZScoreNormalization()
    elif NORMALIZATION_METHOD == 'PERCENTILE':
        return PercentileNormalization()
    else:
        raise ValueError(f"Unknown normalization method: {NORMALIZATION_METHOD}")

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

