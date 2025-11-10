"""
Recommendation system core module.

Handles normalization, vector operations, and statistics calculation
for the roommate matching system.
"""

from .vector_ops import create_vector, euclidean_distance
from .statistics import calculate_parameter_statistics, update_statistics
from .normalization_strategy import NormalizationStrategy
from .ZSCORE_NORMALIZATION import ZScoreNormalization
from .PERCENTILE_NORMALIZATION import PercentileNormalization

__all__ = [
    'create_vector',
    'euclidean_distance',
    'calculate_parameter_statistics',
    'update_statistics',
    'NormalizationStrategy',
    'ZScoreNormalization',
    'PercentileNormalization',
]

