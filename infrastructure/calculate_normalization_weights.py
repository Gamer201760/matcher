"""
Calculate optimal normalization weights to equalize parameter distributions.

This module uses scipy optimization to find normalization weights that minimize
the variance of parameter means after cap-based normalization. This ensures all
parameters contribute equally before importance weights are applied.
"""

import numpy as np
from scipy.optimize import minimize


def generate_sample_data(sample_size, parameters, user_ranges):
    """
    Generate sample data based on typical user ranges.

    Args:
        sample_size: Number of samples to generate
        parameters: List of parameter names
        user_ranges: Dict mapping parameter names to their typical ranges

    Returns:
        Dict mapping parameter names to numpy arrays of sample values
    """
    np.random.seed(42)  # For reproducibility
    sample_data = {}

    for param in parameters:
        if param == 'rooms':
            # Range tuple (min, max)
            min_val, max_val = user_ranges.get(param, (1, 4))
            sample_data[param] = np.random.randint(min_val, max_val + 1, sample_size)

        elif param == 'roommates':
            # Range tuple (min, max)
            min_val, max_val = user_ranges.get(param, (1, 5))
            sample_data[param] = np.random.randint(min_val, max_val + 1, sample_size)

        elif param == 'budget':
            # Range tuple (min, max)
            min_val, max_val = user_ranges.get(param, (5000, 60000))
            sample_data[param] = np.random.uniform(min_val, max_val, sample_size)

        elif param == 'months':
            # List of possible values
            options = user_ranges.get(param, [3, 6, 9, 12, 18, 24, 36])
            sample_data[param] = np.random.choice(options, sample_size)

        else:
            # Default: uniform distribution [0, 1]
            sample_data[param] = np.random.uniform(0, 1, sample_size)

    return sample_data


def calculate_metrics(sample_data, default_caps, norm_weights, parameters):
    """
    Calculate mean and std metrics for current normalization weights.

    Args:
        sample_data: Dict of sample data arrays
        default_caps: Dict of normalization caps
        norm_weights: Dict of current normalization weights
        parameters: List of parameter names

    Returns:
        Tuple of (means_array, stds_array)
    """
    means = []
    stds = []

    for param in parameters:
        # Apply cap-based normalization, then normalization weight
        normalized = (sample_data[param] / default_caps[param]) * norm_weights[param]
        means.append(np.mean(normalized))
        stds.append(np.std(normalized))

    return np.array(means), np.array(stds)


def objective_function(weights_array, sample_data, default_caps, parameters):
    """
    Objective function to minimize - variance of parameter means.

    Lower variance means more equal distributions across all parameters.

    Args:
        weights_array: Array of normalization weights (one per parameter)
        sample_data: Dict of sample data
        default_caps: Dict of normalization caps
        parameters: List of parameter names in order

    Returns:
        Variance of means (scalar to minimize)
    """
    # Convert array to dict
    norm_weights = {param: weights_array[i] for i, param in enumerate(parameters)}

    # Calculate metrics
    means, stds = calculate_metrics(sample_data, default_caps, norm_weights, parameters)

    # Return variance of means (want this close to 0)
    return np.var(means)


def calculate_optimal_normalization_weights(
    sample_size=1000, parameters=None, default_caps=None, user_ranges=None
):
    """
    Calculate optimal normalization weights using scipy optimization.

    This function:
    1. Generates sample data based on typical user ranges
    2. Uses L-BFGS-B optimization to find weights that minimize variance of means
    3. Returns the optimal weights as a dictionary

    Args:
        sample_size: Number of samples to generate (default: 1000)
        parameters: List of parameter names (required)
        default_caps: Dict of normalization caps (required)
        user_ranges: Dict of typical user value ranges (required)

    Returns:
        Dict mapping parameter names to optimal normalization weights

    Example:
        >>> weights = calculate_optimal_normalization_weights(
        ...     sample_size=1000,
        ...     parameters=['rooms', 'roommates', 'budget', 'months'],
        ...     default_caps={'rooms': 10, 'roommates': 10, 'budget': 200000, 'months': 64},
        ...     user_ranges={
        ...         'rooms': (1, 4),
        ...         'roommates': (1, 5),
        ...         'budget': (5000, 60000),
        ...         'months': [3, 6, 9, 12, 18, 24, 36]
        ...     }
        ... )
        >>> print(weights)
        {'rooms': 2.4660, 'roommates': 2.1119, 'budget': 3.8157, 'months': 1.4960}
    """
    if parameters is None or default_caps is None or user_ranges is None:
        raise ValueError('parameters, default_caps, and user_ranges are required')

    # Generate sample data
    sample_data = generate_sample_data(sample_size, parameters, user_ranges)

    # Initial guess - start from uniform weights
    initial_weights = np.ones(len(parameters))

    # Bounds - keep weights reasonable (between 0.1 and 10)
    bounds = [(0.1, 10.0) for _ in parameters]

    # Run optimization
    result = minimize(
        objective_function,
        initial_weights,
        args=(sample_data, default_caps, parameters),
        method='L-BFGS-B',
        bounds=bounds,
    )

    # Convert result to dictionary
    optimal_weights = {param: result.x[i] for i, param in enumerate(parameters)}

    return optimal_weights
