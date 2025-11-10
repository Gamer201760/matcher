"""
Tests for the recommendation system core functionality.

Tests normalization, vector operations, and statistics without Neo4j.
"""
import pytest
import numpy as np
from unittest.mock import Mock, MagicMock
from recommendation.ZSCORE_NORMALIZATION import ZScoreNormalization, DEFAULT_ZSCORE_STATISTICS
from recommendation.PERCENTILE_NORMALIZATION import PercentileNormalization, DEFAULT_PERCENTILE_STATISTICS
from recommendation.vector_ops import create_vector, euclidean_distance
from recommendation.statistics import calculate_parameter_statistics


class TestZScoreNormalization:
    """Test Z-score + sigmoid normalization."""
    
    def setup_method(self):
        """Setup normalizer for each test."""
        self.normalizer = ZScoreNormalization()
    
    def test_normalize_with_default_statistics(self):
        """Test normalization uses default statistics when none provided."""
        # Budget with default stats: mean=30000, std=20000
        result = self.normalizer.normalize(30000, 'budget')
        assert 0.4 < result < 0.6  # Z-score=0 → sigmoid=0.5
    
    def test_normalize_above_mean(self):
        """Test values above mean return > 0.5."""
        stats = {'mean': 100, 'std': 10}
        result = self.normalizer.normalize(110, 'test_param', stats)
        assert result > 0.5
    
    def test_normalize_below_mean(self):
        """Test values below mean return < 0.5."""
        stats = {'mean': 100, 'std': 10}
        result = self.normalizer.normalize(90, 'test_param', stats)
        assert result < 0.5
    
    def test_normalize_zero_std(self):
        """Test handling of zero standard deviation."""
        stats = {'mean': 100, 'std': 0}
        result = self.normalizer.normalize(100, 'test_param', stats)
        assert result == 0.5
    
    def test_normalize_extreme_values(self):
        """Test extreme z-scores are bounded by sigmoid."""
        stats = {'mean': 0, 'std': 1}
        
        # Very large positive z-score
        result_high = self.normalizer.normalize(10, 'test_param', stats)
        assert 0 < result_high < 1
        assert result_high > 0.99
        
        # Very large negative z-score
        result_low = self.normalizer.normalize(-10, 'test_param', stats)
        assert 0 < result_low < 1
        assert result_low < 0.01
    
    def test_default_statistics_exist(self):
        """Test all expected parameters have default statistics."""
        assert 'rooms' in DEFAULT_ZSCORE_STATISTICS
        assert 'roommates' in DEFAULT_ZSCORE_STATISTICS
        assert 'budget' in DEFAULT_ZSCORE_STATISTICS
        assert 'months' in DEFAULT_ZSCORE_STATISTICS
        
        for param, stats in DEFAULT_ZSCORE_STATISTICS.items():
            assert 'mean' in stats
            assert 'std' in stats
    
    def test_statistics_type(self):
        """Test strategy returns correct statistics type."""
        assert self.normalizer.get_statistics_type() == 'mean_std'


class TestPercentileNormalization:
    """Test percentile-based normalization."""
    
    def setup_method(self):
        """Setup normalizer for each test."""
        self.normalizer = PercentileNormalization()
    
    def test_normalize_at_median(self):
        """Test value at median returns ~0.5."""
        # Percentiles: [0, 10, 20, ..., 100]
        percentiles = np.linspace(0, 100, 101)
        stats = {'percentiles': percentiles}
        
        # Value 50 should be at 50th percentile
        result = self.normalizer.normalize(50, 'test_param', stats)
        assert 0.45 < result < 0.55
    
    def test_normalize_minimum_value(self):
        """Test minimum value returns ~0."""
        percentiles = np.array([10, 20, 30, 40, 50, 60, 70, 80, 90, 100])
        stats = {'percentiles': percentiles}
        
        result = self.normalizer.normalize(5, 'test_param', stats)
        assert result == 0.0
    
    def test_normalize_maximum_value(self):
        """Test maximum value returns 1.0."""
        percentiles = np.array([10, 20, 30, 40, 50, 60, 70, 80, 90, 100])
        stats = {'percentiles': percentiles}
        
        result = self.normalizer.normalize(110, 'test_param', stats)
        assert result == 1.0
    
    def test_outlier_handling(self):
        """Test that extreme outliers don't break the system."""
        # Normal range: 10-100, with one outlier at 1M
        percentiles = np.linspace(10, 100, 101)
        stats = {'percentiles': percentiles}
        
        # 1M is way beyond the range - should just return 1.0
        result = self.normalizer.normalize(1_000_000, 'test_param', stats)
        assert result == 1.0
        
        # Value still works for normal users
        result_normal = self.normalizer.normalize(50, 'test_param', stats)
        assert 0.4 < result_normal < 0.6
    
    def test_percentile_precision(self):
        """Test percentile calculation precision."""
        # Create percentiles for budget: 5k to 60k
        percentiles = np.linspace(5000, 60000, 101)
        stats = {'percentiles': percentiles}
        
        # 30k is roughly middle
        result = self.normalizer.normalize(30000, 'budget', stats)
        assert 0.40 < result < 0.50
    
    def test_default_statistics_exist(self):
        """Test all expected parameters have default percentile statistics."""
        assert 'rooms' in DEFAULT_PERCENTILE_STATISTICS
        assert 'roommates' in DEFAULT_PERCENTILE_STATISTICS
        assert 'budget' in DEFAULT_PERCENTILE_STATISTICS
        assert 'months' in DEFAULT_PERCENTILE_STATISTICS
        
        for param, stats in DEFAULT_PERCENTILE_STATISTICS.items():
            assert 'percentiles' in stats
            assert len(stats['percentiles']) > 0
    
    def test_statistics_type(self):
        """Test strategy returns correct statistics type."""
        assert self.normalizer.get_statistics_type() == 'percentiles'


class TestVectorOperations:
    """Test vector creation and distance calculation."""
    
    def test_create_vector_basic(self):
        """Test basic vector creation without weights."""
        values = {'rooms': 2, 'roommates': 1, 'budget': 10000, 'months': 12}
        parameters = ['rooms', 'roommates', 'budget', 'months']
        
        vector = create_vector(values, parameters)
        
        assert len(vector) == 4
        assert all(0 <= v <= 1 for v in vector)
    
    def test_create_vector_with_weights(self):
        """Test vector creation with importance weights."""
        values = {'rooms': 2, 'roommates': 1, 'budget': 10000, 'months': 12}
        parameters = ['rooms', 'roommates', 'budget', 'months']
        weights = {'rooms': 2.0, 'roommates': 1.0, 'budget': 1.5, 'months': 1.0}
        
        vector_unweighted = create_vector(values, parameters, weights=None)
        vector_weighted = create_vector(values, parameters, weights=weights)
        
        # Weighted vector should have different values
        assert len(vector_weighted) == 4
        # The rooms dimension should be scaled by 2.0
        assert vector_weighted[0] > vector_unweighted[0]
    
    def test_create_vector_missing_parameter(self):
        """Test vector creation with missing parameter."""
        values = {'rooms': 2, 'budget': 10000}  # Missing roommates and months
        parameters = ['rooms', 'roommates', 'budget', 'months']
        
        vector = create_vector(values, parameters)
        
        assert len(vector) == 4
        assert vector[1] == 0.0  # Missing roommates
        assert vector[3] == 0.0  # Missing months
    
    def test_create_vector_custom_statistics(self):
        """Test vector creation with custom statistics."""
        values = {'param1': 50, 'param2': 100}
        parameters = ['param1', 'param2']
        statistics = {
            'param1': {'mean': 50, 'std': 10},
            'param2': {'mean': 100, 'std': 20}
        }
        
        vector = create_vector(values, parameters, statistics=statistics)
        
        assert len(vector) == 2
        # Both values equal their means, so z-score=0, sigmoid≈0.5
        assert 0.49 < vector[0] < 0.51
        assert 0.49 < vector[1] < 0.51
    
    def test_euclidean_distance_identical(self):
        """Test distance between identical vectors is zero."""
        vec1 = [0.5, 0.5, 0.5, 0.5]
        vec2 = [0.5, 0.5, 0.5, 0.5]
        
        distance = euclidean_distance(vec1, vec2)
        assert distance == 0.0
    
    def test_euclidean_distance_different(self):
        """Test distance between different vectors."""
        vec1 = [0.0, 0.0, 0.0, 0.0]
        vec2 = [1.0, 1.0, 1.0, 1.0]
        
        distance = euclidean_distance(vec1, vec2)
        assert 0 < distance <= 1.0
    
    def test_euclidean_distance_normalized(self):
        """Test distance is normalized to [0, 1]."""
        vec1 = [0.2, 0.3, 0.4, 0.5]
        vec2 = [0.8, 0.7, 0.6, 0.9]
        
        distance = euclidean_distance(vec1, vec2)
        assert 0 <= distance <= 1.0
    
    def test_euclidean_distance_empty_vectors(self):
        """Test distance with empty vectors."""
        distance = euclidean_distance([], [])
        assert distance == 1.0
    
    def test_euclidean_distance_mismatched_length(self):
        """Test distance with different length vectors."""
        vec1 = [0.5, 0.5]
        vec2 = [0.5, 0.5, 0.5]
        
        distance = euclidean_distance(vec1, vec2)
        assert distance == 1.0


class TestStatistics:
    """Test statistics calculation with mocked Neo4j."""
    
    def test_calculate_statistics_zscore_method(self):
        """Test statistics calculation for Z-score method."""
        # Mock session
        mock_session = Mock()
        
        # Mock data: 20 users with varied parameters
        mock_data = [
            {'rooms': i % 4 + 1, 'roommates': i % 5 + 1, 
             'budget': 10000 + i * 1000, 'months': [6, 12, 24][i % 3]}
            for i in range(20)
        ]
        
        mock_session.run.return_value = [Mock(data=lambda d=d: d) for d in mock_data]
        
        normalizer = ZScoreNormalization()
        parameters = ['rooms', 'roommates', 'budget', 'months']
        statistics = calculate_parameter_statistics(mock_session, parameters, normalizer)
        
        assert statistics is not None
        assert 'rooms' in statistics
        assert 'budget' in statistics
        
        for param in ['rooms', 'roommates', 'budget', 'months']:
            if param in statistics:
                assert 'mean' in statistics[param]
                assert 'std' in statistics[param]
    
    def test_calculate_statistics_percentile_method(self):
        """Test statistics calculation for percentile method."""
        # Mock session
        mock_session = Mock()
        
        # Mock data: 20 users
        mock_data = [
            {'rooms': i % 4 + 1, 'roommates': i % 5 + 1, 
             'budget': 10000 + i * 1000, 'months': [6, 12, 24][i % 3]}
            for i in range(20)
        ]
        
        mock_session.run.return_value = [Mock(data=lambda d=d: d) for d in mock_data]
        
        normalizer = PercentileNormalization()
        parameters = ['rooms', 'roommates', 'budget', 'months']
        statistics = calculate_parameter_statistics(mock_session, parameters, normalizer)
        
        assert statistics is not None
        
        for param in ['rooms', 'roommates', 'budget', 'months']:
            if param in statistics:
                assert 'percentiles' in statistics[param]
                assert len(statistics[param]['percentiles']) == 101
    
    def test_calculate_statistics_insufficient_data(self):
        """Test statistics returns None with insufficient data."""
        mock_session = Mock()
        
        # Only 5 users (< 10 minimum)
        mock_data = [
            {'rooms': 2, 'roommates': 1, 'budget': 10000, 'months': 12}
            for _ in range(5)
        ]
        
        mock_session.run.return_value = [Mock(data=lambda d=d: d) for d in mock_data]
        
        normalizer = ZScoreNormalization()
        parameters = ['rooms', 'roommates', 'budget', 'months']
        statistics = calculate_parameter_statistics(mock_session, parameters, normalizer)
        
        # Should return None or empty dict
        assert statistics is None or not statistics
    
    def test_calculate_statistics_empty_database(self):
        """Test statistics with no users."""
        mock_session = Mock()
        mock_session.run.return_value = []
        
        normalizer = ZScoreNormalization()
        parameters = ['rooms', 'roommates', 'budget', 'months']
        statistics = calculate_parameter_statistics(mock_session, parameters, normalizer)
        
        assert statistics is None
    
    def test_calculate_statistics_outlier_filtering(self):
        """Test that outliers are filtered (5% on each end) for Z-score method."""
        mock_session = Mock()
        
        # Create data with clear outliers
        mock_data = []
        # 90 normal values around 100
        for i in range(90):
            mock_data.append({
                'rooms': 2, 'roommates': 2,
                'budget': 100 + np.random.randint(-10, 10),
                'months': 12
            })
        
        # 5 low outliers
        for _ in range(5):
            mock_data.append({
                'rooms': 2, 'roommates': 2,
                'budget': 10,
                'months': 12
            })
        
        # 5 high outliers
        for _ in range(5):
            mock_data.append({
                'rooms': 2, 'roommates': 2,
                'budget': 1000,
                'months': 12
            })
        
        mock_session.run.return_value = [Mock(data=lambda d=d: d) for d in mock_data]
        
        normalizer = ZScoreNormalization()
        parameters = ['budget']
        statistics = calculate_parameter_statistics(mock_session, parameters, normalizer)
        
        assert statistics is not None
        # Mean should be close to 100, not affected by outliers
        assert 80 < statistics['budget']['mean'] < 120


class TestIntegration:
    """Integration tests for the full recommendation pipeline."""
    
    def test_full_pipeline_similarity_zscore(self):
        """Test complete pipeline with Z-score: create vectors and compute similarity."""
        # User preferences
        user1 = {'rooms': 2, 'roommates': 1, 'budget': 15000, 'months': 12}
        user2 = {'rooms': 2, 'roommates': 1, 'budget': 16000, 'months': 12}
        user3 = {'rooms': 4, 'roommates': 4, 'budget': 50000, 'months': 36}
        
        parameters = ['rooms', 'roommates', 'budget', 'months']
        normalizer = ZScoreNormalization()
        
        # Create vectors
        vec1 = create_vector(user1, parameters, normalizer=normalizer)
        vec2 = create_vector(user2, parameters, normalizer=normalizer)
        vec3 = create_vector(user3, parameters, normalizer=normalizer)
        
        # Calculate distances
        dist_1_2 = euclidean_distance(vec1, vec2)
        dist_1_3 = euclidean_distance(vec1, vec3)
        
        # User1 should be closer to User2 than User3
        assert dist_1_2 < dist_1_3
    
    def test_full_pipeline_similarity_percentile(self):
        """Test complete pipeline with percentile: create vectors and compute similarity."""
        # User preferences
        user1 = {'rooms': 2, 'roommates': 1, 'budget': 15000, 'months': 12}
        user2 = {'rooms': 2, 'roommates': 1, 'budget': 16000, 'months': 12}
        user3 = {'rooms': 4, 'roommates': 4, 'budget': 50000, 'months': 36}
        
        parameters = ['rooms', 'roommates', 'budget', 'months']
        normalizer = PercentileNormalization()
        
        # Create vectors
        vec1 = create_vector(user1, parameters, normalizer=normalizer)
        vec2 = create_vector(user2, parameters, normalizer=normalizer)
        vec3 = create_vector(user3, parameters, normalizer=normalizer)
        
        # Calculate distances
        dist_1_2 = euclidean_distance(vec1, vec2)
        dist_1_3 = euclidean_distance(vec1, vec3)
        
        # User1 should be closer to User2 than User3
        assert dist_1_2 < dist_1_3
    
    def test_weighted_vs_unweighted_similarity(self):
        """Test that importance weights affect similarity scores."""
        user1 = {'rooms': 1, 'roommates': 1, 'budget': 10000, 'months': 12}
        user2 = {'rooms': 4, 'roommates': 1, 'budget': 10000, 'months': 12}
        
        parameters = ['rooms', 'roommates', 'budget', 'months']
        
        # Heavily weight rooms
        weights = {'rooms': 10.0, 'roommates': 1.0, 'budget': 1.0, 'months': 1.0}
        
        # Without weights
        vec1_unweighted = create_vector(user1, parameters, weights=None)
        vec2_unweighted = create_vector(user2, parameters, weights=None)
        dist_unweighted = euclidean_distance(vec1_unweighted, vec2_unweighted)
        
        # With weights
        vec1_weighted = create_vector(user1, parameters, weights=weights)
        vec2_weighted = create_vector(user2, parameters, weights=weights)
        dist_weighted = euclidean_distance(vec1_weighted, vec2_weighted)
        
        # Weighted distance should be larger due to rooms difference
        assert dist_weighted > dist_unweighted
    
    def test_normalization_consistency_zscore(self):
        """Test that Z-score normalization produces consistent results."""
        normalizer = ZScoreNormalization()
        value = 12
        param = 'months'
        stats = {'mean': 12, 'std': 6}
        
        # Multiple calls should return same result
        result1 = normalizer.normalize(value, param, stats)
        result2 = normalizer.normalize(value, param, stats)
        result3 = normalizer.normalize(value, param, stats)
        
        assert result1 == result2 == result3
    
    def test_normalization_consistency_percentile(self):
        """Test that percentile normalization produces consistent results."""
        normalizer = PercentileNormalization()
        value = 50
        param = 'budget'
        stats = {'percentiles': np.linspace(0, 100, 101)}
        
        # Multiple calls should return same result
        result1 = normalizer.normalize(value, param, stats)
        result2 = normalizer.normalize(value, param, stats)
        result3 = normalizer.normalize(value, param, stats)
        
        assert result1 == result2 == result3
    
    def test_vector_dimension_consistency(self):
        """Test that vectors always have correct dimensions."""
        values = {'rooms': 2, 'roommates': 1, 'budget': 10000, 'months': 12}
        parameters = ['rooms', 'roommates', 'budget', 'months']
        
        vec1 = create_vector(values, parameters)
        vec2 = create_vector(values, parameters, weights={'rooms': 2.0})
        
        assert len(vec1) == len(parameters)
        assert len(vec2) == len(parameters)
        assert len(vec1) == len(vec2)

