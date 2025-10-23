"""
Create normalized preference vectors for users and groups and compare them with cosine distance.

- Normalizes each parameter to [0, 1] using simple, capped transforms
  consistent with prior distance capping (rooms/roommates cap at 2, months cap at 36).
- Supports optional weighting of vector components for GROUPS.
"""
from math import sqrt
from .config import GROUP_PARAMETER_WEIGHTS, WEIGHT_MULTIPLIER, DEFAULT_CAPS


def _clamp(value, min_value, max_value):
    """Clamp a numeric value to the inclusive range [min_value, max_value]."""
    if value < min_value:
        return min_value
    if value > max_value:
        return max_value
    return value


def normalize_rooms(x, cap=None):
    """Normalize desired rooms to [0, 1] by capping at cap and dividing by cap."""
    cap = cap or DEFAULT_CAPS['rooms']
    x = _clamp(x, 0, cap)
    return x / cap

    
def normalize_roommates(x, cap=None):
    """Normalize desired roommates to [0, 1] by capping at cap and dividing by cap."""
    cap = cap or DEFAULT_CAPS['roommates']
    x = _clamp(x, 0, cap)
    return x / cap


def normalize_budget(x, cap=None):
    """Normalize budget to [0, 1] by clamping to [0, cap] and dividing by cap."""
    cap = cap or DEFAULT_CAPS['budget']
    if cap <= 0:
        return 0.0
    x = _clamp(x, 0, cap)
    return x / float(cap)


def normalize_months(x, cap=None):
    """Normalize months to [0, 1] by clamping to [1, cap] and dividing by cap."""
    cap = cap or DEFAULT_CAPS['months']
    x = _clamp(x, 1, cap)
    return x / float(cap)

available_parameters = {
    'rooms': normalize_rooms,
    'roommates': normalize_roommates,
    'budget': normalize_budget,
    'months': normalize_months
}

# Weights imported from config.py
# group_parameter_weights is now GROUP_PARAMETER_WEIGHTS from config
group_parameter_weights = GROUP_PARAMETER_WEIGHTS


def create_user_vector(user:dict, parameters:list, caps:dict=None):
    """Create an unweighted normalized vector in the order of `parameters`."""
    vector = []
    caps = caps or {}
    for param in parameters:
        if param in available_parameters and param in user:
            normalizer = available_parameters[param]
            if param in ('budget', 'months'):
                # Pass optional cap if provided
                cap_value = caps.get(param)
                if cap_value is not None:
                    vector.append(normalizer(user[param], cap_value))
                else:
                    vector.append(normalizer(user[param]))
            else:
                vector.append(normalizer(user[param]))
        else:
            vector.append(0.0)
    return vector

def create_group_vector_with_weights(values:dict, parameters:list, weights:dict, caps:dict=None):
    """Create a weighted normalized vector for a GROUP using group parameter values.

    values: mapping of parameter name to raw numeric value (e.g., averaged across members)
    parameters: ordered list of parameter names
    weights: group weights mapping
    caps: optional caps for normalizers
    """
    base_vector = create_user_vector(values, parameters, caps)
    weighted_vector = []
    for i, param in enumerate(parameters):
        w = weights.get(param, 1.0)
        weighted_vector.append(base_vector[i] * w)
    return weighted_vector


# Commented out - using Euclidean distance instead
# def cosine_distance(vec1:list, vec2:list) -> float:
#     """Compute cosine distance = 1 - cosine similarity for two equal-length vectors."""
#     if not vec1 or not vec2 or len(vec1) != len(vec2):
#         return 1.0
#     dot = sum(a*b for a, b in zip(vec1, vec2))
#     norm1 = sqrt(sum(a*a for a in vec1))
#     norm2 = sqrt(sum(b*b for b in vec2))
#     if norm1 == 0.0 or norm2 == 0.0:
#         return 1.0
#     return 1.0 - (dot / (norm1 * norm2))


def euclidean_distance(vec1:list, vec2:list) -> float:
    """Compute Euclidean distance between two equal-length vectors.
    
    Returns normalized distance in [0, 1] range where:
    - 0 = identical vectors
    - 1 = maximum distance
    """
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 1.0
    
    # Calculate Euclidean distance (L2 norm)
    squared_diff = sum((a - b) ** 2 for a, b in zip(vec1, vec2))
    distance = sqrt(squared_diff)
    
    # Normalize to [0, 1] range
    # Max possible distance for normalized vectors is sqrt(2) for opposing unit vectors
    # We'll use sqrt(len(vec1)) as a conservative max for normalized [0,1] vectors
    max_distance = sqrt(len(vec1))
    normalized_distance = min(1.0, distance / max_distance)
    
    return normalized_distance


if __name__ == "__main__":
    # Example values (as a single-member group)
    group_a = {
        'rooms': 1,
        'roommates': 1,
        'budget': 10000,
        'months': 12
    }
    group_b = {
        'rooms': 2,
        'roommates': 2,
        'budget': 15000,
        'months': 6
    }

    parameters = ['rooms', 'roommates', 'budget', 'months']
    weights = group_parameter_weights

    # Optional caps override (e.g., budget upper bound)
    caps = {'budget': 200000, 'months': 36}

    vec_a = create_group_vector_with_weights(group_a, parameters, weights, caps)
    vec_b = create_group_vector_with_weights(group_b, parameters, weights, caps)

    dist_weighted = euclidean_distance(vec_a, vec_b)

    print(f"Group A weighted vector: {vec_a}")
    print(f"Group B weighted vector: {vec_b}")
    print(f"Euclidean distance (group, weighted): {dist_weighted}")
    print(f"Similarity score (group, weighted): {round((1 - dist_weighted)*100, 2)}%")