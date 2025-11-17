"""Vector creation and distance calculation for recommendation system."""

from math import sqrt


def create_vector(values, parameters, statistics=None, weights=None, normalizer=None):
    """
    Create normalized vector with optional importance weights.

    Args:
        values: Dict mapping parameter names to raw values
        parameters: Ordered list of parameter names
        statistics: Dict of parameter statistics for normalization
        weights: Optional importance weights (applied after normalization)
        normalizer: NormalizationStrategy instance (defaults to configured strategy)

    Returns:
        List of normalized (and optionally weighted) values
    """
    # Import here to avoid circular dependency
    if normalizer is None:
        from infrastructure.config import get_normalizer

        normalizer = get_normalizer()

    vector = []
    for param in parameters:
        if param in values:
            # Extract parameter-specific statistics
            param_stats = statistics.get(param) if statistics else None
            normalized = normalizer.normalize(values[param], param, param_stats)

            # Apply importance weight if provided
            if weights and param in weights:
                normalized *= weights[param]

            vector.append(normalized)
        else:
            vector.append(0.0)

    return vector


def euclidean_distance(vec1, vec2):
    """
    Compute Euclidean distance between two vectors.

    Returns:
        Normalized distance in [0, 1] range
    """
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 1.0

    squared_diff = sum((a - b) ** 2 for a, b in zip(vec1, vec2))
    distance = sqrt(squared_diff)

    # Normalize by maximum possible distance
    max_distance = sqrt(len(vec1))
    return min(1.0, distance / max_distance)
