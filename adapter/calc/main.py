import os

import redis
from dotenv import load_dotenv

from infrastructure.config import PARAMETERS
from infrastructure.logging_utils import setup_logger
from infrastructure.neo4j.connection import ensure_constraints_and_index, get_driver
from repository.group_recommendation_cache import (
    CacheGroupRecommendationRepositoryRedis,
)
from repository.group_recommendation_repository import GroupRecommendationRepository
from repository.group_repository import GroupRepository
from usecase.cache import CacheRecomendationUsecase

logger = setup_logger('calc')

load_dotenv()


def main():
    logger.info('Start calculation')
    redis_client = redis.Redis(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', '6379')),
        db=0,
        decode_responses=True,
    )
    driver = get_driver(
        os.getenv('NEO4J_URI', ''),
        os.getenv('NEO4J_USERNAME', ''),
        os.getenv('NEO4J_PASSWORD', ''),
    )
    with driver.session() as session:
        ensure_constraints_and_index(session, dims=len(PARAMETERS))

    group_repo = GroupRepository(driver)
    recomend_repo = GroupRecommendationRepository(driver)
    cache_repo = CacheGroupRecommendationRepositoryRedis(redis_client)

    cache = CacheRecomendationUsecase(cache_repo, recomend_repo, group_repo)
    cache.execute()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info('Goodbye!')
