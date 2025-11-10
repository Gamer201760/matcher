"""Calculate parameter statistics from user data with outlier filtering."""

import numpy as np


def calculate_parameter_statistics(session, parameters, strategy):
    """
    Calculate statistics for each parameter from Neo4j user data.
    
    Statistics type depends on normalization strategy:
    - Z-score: Calculate mean and std (with 5% outlier filtering)
    - Percentile: Calculate percentile points (p0 to p100)
    
    Args:
        session: Neo4j session
        parameters: List of parameter names
        strategy: NormalizationStrategy instance
    
    Returns:
        Dict mapping parameter names to statistics dict
    """
    query = """
    MATCH (u:User)
    RETURN u.rooms as rooms, u.roommates as roommates, 
           u.budget as budget, u.months as months
    """
    
    result = session.run(query)
    records = [r.data() for r in result]
    
    if not records:
        return None
    
    statistics = {}
    stats_type = strategy.get_statistics_type()
    
    for param in parameters:
        values = [r[param] for r in records if r.get(param) is not None]
        
        if len(values) < 10:
            # Not enough data, use defaults
            continue
        
        values_array = np.array(values)
        
        if stats_type == 'mean_std':
            # Z-score strategy: calculate mean/std with outlier filtering
            p5 = np.percentile(values_array, 5)
            p95 = np.percentile(values_array, 95)
            filtered = values_array[(values_array >= p5) & (values_array <= p95)]
            
            if len(filtered) > 0:
                statistics[param] = {
                    'mean': float(np.mean(filtered)),
                    'std': float(np.std(filtered))
                }
        
        elif stats_type == 'percentiles':
            # Percentile strategy: calculate 101 percentile points (p0 to p100)
            percentiles = np.percentile(values_array, range(0, 101))
            statistics[param] = {
                'percentiles': percentiles
            }
        
        else:
            raise ValueError(f"Unknown statistics type: {stats_type}")
    
    return statistics if statistics else None


def update_statistics(driver, parameters, strategy):
    """
    Update parameter statistics from current user data.
    
    Args:
        driver: Neo4j driver
        parameters: List of parameter names
        strategy: NormalizationStrategy instance
    
    Returns:
        Tuple of (statistics_dict, user_count)
    """
    with driver.session() as session:
        # Get user count
        count_result = session.run("MATCH (u:User) RETURN count(u) as count")
        user_count = count_result.single()['count']
        
        # Calculate statistics
        statistics = calculate_parameter_statistics(session, parameters, strategy)
        
        return statistics, user_count
