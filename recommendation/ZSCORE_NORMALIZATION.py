"""Z-score normalization with sigmoid transformation to [0,1] range."""

from math import exp
from .normalization_strategy import NormalizationStrategy


# Default statistics used when insufficient user data is available
DEFAULT_ZSCORE_STATISTICS = {
    'rooms': {'mean': 2.5, 'std': 1.0},
    'roommates': {'mean': 3.0, 'std': 1.5},
    'budget': {'mean': 30000, 'std': 20000},
    'months': {'mean': 12, 'std': 8},
}


class ZScoreNormalization(NormalizationStrategy):
    """
    Z-score + sigmoid normalization strategy.
    
    Normalizes using: sigmoid((value - mean) / std)
    - Centers data around mean
    - Scales by standard deviation
    - Maps to [0, 1] via sigmoid function
    
    Advantages:
    - Well-established statistical method
    - Good for normally distributed data
    - Handles extreme values smoothly via sigmoid
    
    Disadvantages:
    - Sensitive to outliers (without filtering)
    - Assumes roughly Gaussian distribution
    """
    
    def normalize(self, value, param_name, statistics=None):
        """
        Normalize parameter using Z-score + sigmoid.
        
        Args:
            value: Raw parameter value
            param_name: Parameter name ('rooms', 'budget', etc.)
            statistics: Dict with 'mean' and 'std' for the parameter
        
        Returns:
            Normalized value in [0, 1] range
        """
        stats = statistics or self.get_default_statistics(param_name)
        mean = stats['mean']
        std = stats['std']
        
        # Avoid division by zero
        if std == 0:
            return 0.5
        
        # Z-score
        z = (value - mean) / std
        
        # Sigmoid to [0, 1]
        return 1.0 / (1.0 + exp(-z))
    
    def get_statistics_type(self):
        """Return 'mean_std' as the statistics type."""
        return 'mean_std'
    
    def get_default_statistics(self, param_name):
        """
        Get default mean/std statistics for a parameter.
        
        Args:
            param_name: Parameter name
        
        Returns:
            Dict with 'mean' and 'std' keys
        """
        return DEFAULT_ZSCORE_STATISTICS.get(param_name, {'mean': 0, 'std': 1})

