"""Z-score normalization with sigmoid transformation to [0,1] range."""

from math import exp

# Default statistics used when insufficient user data is available
DEFAULT_STATISTICS = {
    'rooms': {'mean': 2.5, 'std': 1.0},
    'roommates': {'mean': 3.0, 'std': 1.5},
    'budget': {'mean': 30000, 'std': 20000},
    'months': {'mean': 12, 'std': 8},
}


def normalize_parameter(value, param_name, statistics=None):
    """
    Normalize parameter using Z-score + sigmoid.
    
    Args:
        value: Raw parameter value
        param_name: Parameter name ('rooms', 'budget', etc.)
        statistics: Dict with 'mean' and 'std' for the parameter
    
    Returns:
        Normalized value in [0, 1] range
    """
    stats = statistics or DEFAULT_STATISTICS.get(param_name, {'mean': 0, 'std': 1})
    mean = stats['mean']
    std = stats['std']
    
    # Avoid division by zero
    if std == 0:
        return 0.5
    
    # Z-score
    z = (value - mean) / std
    
    # Sigmoid to [0, 1]
    return 1.0 / (1.0 + exp(-z))

