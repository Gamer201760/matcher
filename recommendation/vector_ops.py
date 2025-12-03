"""Vector creation and distance calculation for recommendation system."""

import math
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


def mean_geo_coords(members: list[dict[str, float]]) -> tuple[float, float]:
    """
    Calculate the geographic mean (centroid) of coordinates using spherical geometry.

    This function computes the mean of geographic coordinates on a sphere, which is
    more accurate than simple arithmetic mean for coordinates that span large distances
    or cross the antimeridian.

    Args:
        members: List of dicts with 'geo_lat' and 'geo_lon' keys in degrees

    Returns:
        Tuple of (lat, lon) in degrees

    Raises:
        ValueError: If members list is empty
    """
    if not members:
        raise ValueError("No members for geo mean")

    x = y = z = 0.0
    for m in members:
        lat_deg = m["geo_lat"]
        lon_deg = m["geo_lon"]

        lat = math.radians(lat_deg)
        lon = math.radians(lon_deg)

        x += math.cos(lat) * math.cos(lon)
        y += math.cos(lat) * math.sin(lon)
        z += math.sin(lat)

    n = len(members)
    x /= n
    y /= n
    z /= n

    hyp = math.sqrt(x * x + y * y)
    lat = math.atan2(z, hyp)
    lon = math.atan2(y, x)

    return math.degrees(lat), math.degrees(lon)

if __name__ == "__main__":
    members = [
        {"geo_lat": 55, "geo_lon": 37},
        {"geo_lat": 59, "geo_lon": 30},
    ]
    avg_lat, avg_lon = mean_geo_coords(members)
    print(avg_lat, avg_lon)