"""Abstract base class for normalization strategies."""

from abc import ABC, abstractmethod


class NormalizationStrategy(ABC):
    """
    Abstract interface for normalization strategies.
    
    Defines the contract that all normalization implementations must follow.
    """
    
    @abstractmethod
    def normalize(self, value, param_name, statistics=None):
        """
        Normalize a parameter value to [0, 1] range.
        
        Args:
            value: Raw parameter value
            param_name: Parameter name (e.g., 'rooms', 'budget')
            statistics: Statistics dict for this parameter
        
        Returns:
            Normalized value in [0, 1] range
        """
        pass
    
    @abstractmethod
    def get_statistics_type(self):
        """
        Return the type of statistics this strategy requires.
        
        Returns:
            String describing statistics type (e.g., 'mean_std', 'percentiles')
        """
        pass
    
    @abstractmethod
    def get_default_statistics(self, param_name):
        """
        Get default statistics for a parameter when insufficient data exists.
        
        Args:
            param_name: Parameter name
        
        Returns:
            Dict with default statistics for this strategy
        """
        pass

