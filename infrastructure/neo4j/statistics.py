"""
Parameter statistics utilities for Neo4j-backed data.

This module provides a reusable helper to refresh parameter statistics
(mean/std or percentiles) from the current database contents and store
them in the global configuration for downstream consumers.
"""

import os
from typing import Iterable, Optional, Tuple

from recommendation.statistics import update_statistics

from ..config import PARAMETERS, get_normalizer, set_parameter_statistics
from .connection import get_driver


def update_parameter_statistics(
    driver=None,
    parameters: Optional[Iterable[str]] = None,
    normalizer=None,
) -> Tuple[Optional[dict], int]:
    """
    Recalculate parameter statistics from Neo4j user data and update config.

    Args:
        driver: Optional Neo4j driver. If not provided, one is created
            using environment variables NEO4J_URI/NEO4J_USERNAME/NEO4J_PASSWORD.
        parameters: Iterable of parameter names to calculate statistics for.
            Defaults to PARAMETERS from config.
        normalizer: NormalizationStrategy instance. Defaults to the configured
            normalizer from config.

    Returns:
        Tuple of (statistics_dict or None, user_count).
        Statistics are only applied to config when available and user_count >= 10.
    """
    created_driver = False

    if parameters is None:
        parameters = PARAMETERS

    if normalizer is None:
        normalizer = get_normalizer()

    if driver is None:
        created_driver = True
        driver = get_driver(
            os.getenv('NEO4J_URI', ''),
            os.getenv('NEO4J_USERNAME', ''),
            os.getenv('NEO4J_PASSWORD', ''),
        )

    statistics, user_count = update_statistics(driver, list(parameters), normalizer)

    # Update global config only when we have enough data
    if statistics:
        set_parameter_statistics(statistics)

    if created_driver and driver is not None:
        driver.close()

    return statistics, user_count
