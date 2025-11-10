"""
Recommendation system core module.

Handles normalization, vector operations, and statistics calculation
for the roommate matching system.
"""

from .normalization import normalize_parameter
from .vector_ops import create_vector, euclidean_distance
from .statistics import calculate_parameter_statistics, update_statistics

__all__ = [
    'normalize_parameter',
    'create_vector',
    'euclidean_distance',
    'calculate_parameter_statistics',
    'update_statistics',
]

