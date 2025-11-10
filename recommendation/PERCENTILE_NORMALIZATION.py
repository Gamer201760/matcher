"""Percentile-based normalization - maps values to their percentile rank."""

import numpy as np
from .normalization_strategy import NormalizationStrategy


# Default percentile points (p0 to p100) when insufficient data exists
DEFAULT_PERCENTILE_STATISTICS = {
    'rooms': {
        'percentiles': np.array([1, 1, 1, 2, 2, 2, 2, 2, 3, 3, 3] + [3]*89 + [4])
    },
    'roommates': {
        'percentiles': np.array([1, 1, 1, 1, 2, 2, 2, 3, 3, 3, 4] + [4]*89 + [5])
    },
    'budget': {
        'percentiles': np.linspace(5000, 60000, 101)
    },
    'months': {
        'percentiles': np.array([3]*10 + [6]*15 + [9]*15 + [12]*30 + [18]*15 + [24]*10 + [36]*6)
    },
}


class PercentileNormalization(NormalizationStrategy):
    """
    Percentile-based normalization strategy.
    
    Maps each value to its percentile rank in the population [0, 1].
    Example: If 70% of users have budget < yours, your normalized value is 0.70
    
    Advantages:
    - Completely outlier-proof (1M budget just becomes 100th percentile)
    - Works for any distribution shape
    - Intuitive interpretation ("top 10% for budget")
    - No statistics corruption possible
    
    Disadvantages:
    - Requires storing percentile points or full value arrays
    - More memory intensive than mean/std
    """
    
    def normalize(self, value, param_name, statistics=None):
        """
        Normalize parameter to its percentile rank [0, 1].
        
        Args:
            value: Raw parameter value
            param_name: Parameter name
            statistics: Dict with 'percentiles' array (101 points from p0 to p100)
        
        Returns:
            Percentile rank in [0, 1] range
        """
        stats = statistics or self.get_default_statistics(param_name)
        percentiles = stats['percentiles']
        
        # Find where value fits in the percentile distribution
        # searchsorted returns the index where value would be inserted
        rank = np.searchsorted(percentiles, value, side='right')
        
        # Convert to percentile (0-100 scale, then normalize to 0-1)
        percentile = rank / len(percentiles)
        
        # Clamp to [0, 1]
        return min(1.0, max(0.0, percentile))
    
    def get_statistics_type(self):
        """Return 'percentiles' as the statistics type."""
        return 'percentiles'
    
    def get_default_statistics(self, param_name):
        """
        Get default percentile points for a parameter.
        
        Args:
            param_name: Parameter name
        
        Returns:
            Dict with 'percentiles' array (101 points)
        """
        default = DEFAULT_PERCENTILE_STATISTICS.get(param_name)
        if default is not None:
            return default
        
        # Fallback: uniform distribution [0, 100]
        return {'percentiles': np.linspace(0, 100, 101)}

