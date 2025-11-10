"""Calculate parameter statistics from user data with outlier filtering."""

import numpy as np


def calculate_parameter_statistics(session, parameters):
    """
    Calculate mean and std for each parameter from Neo4j user data.
    
    Filters outliers by excluding bottom 5% and top 5% using percentiles.
    
    Args:
        session: Neo4j session
        parameters: List of parameter names
    
    Returns:
        Dict mapping parameter names to {'mean': X, 'std': Y}
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
    for param in parameters:
        values = [r[param] for r in records if r.get(param) is not None]
        
        if len(values) < 10:
            # Not enough data, return None for this parameter
            continue
        
        values_array = np.array(values)
        
        # Filter outliers: exclude bottom 5% and top 5%
        p5 = np.percentile(values_array, 5)
        p95 = np.percentile(values_array, 95)
        filtered = values_array[(values_array >= p5) & (values_array <= p95)]
        
        if len(filtered) > 0:
            statistics[param] = {
                'mean': float(np.mean(filtered)),
                'std': float(np.std(filtered))
            }
    
    return statistics if statistics else None


def update_statistics(driver, parameters):
    """
    Update parameter statistics from current user data.
    
    Args:
        driver: Neo4j driver
        parameters: List of parameter names
    
    Returns:
        Tuple of (statistics_dict, user_count)
    """
    with driver.session() as session:
        # Get user count
        count_result = session.run("MATCH (u:User) RETURN count(u) as count")
        user_count = count_result.single()['count']
        
        # Calculate statistics
        statistics = calculate_parameter_statistics(session, parameters)
        
        return statistics, user_count

