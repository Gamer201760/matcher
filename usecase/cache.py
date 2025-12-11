from infrastructure.logging_utils import setup_logger
from usecase.interface import (
    CacheGroupRecomendationRepository,
    GroupRecomendationRepository,
    GroupRepository,
)

logger = setup_logger('cache')


class CacheRecomendationUsecase:
    def __init__(
        self,
        cache_repo: CacheGroupRecomendationRepository,
        rec_repo: GroupRecomendationRepository,
        group_repo: GroupRepository,
        batch_size: int = 100,
    ) -> None:
        self._cache_repo = cache_repo
        self._rec_repo = rec_repo
        self._group_repo = group_repo
        self._batch_size = batch_size

    def execute(self) -> None:
        logger.debug('Run calculating cache')
        i = 0
        for group_id, user_ids in self._group_repo.get_all():
            logger.debug(f'Execute for {group_id} with users {user_ids}')
            if i == self._batch_size:
                self._cache_repo.commit()
                logger.debug(f'Commit {self._batch_size} groups to cache')
                i = 0
            recomm = self._rec_repo.execute(group_id)
            for user_id in user_ids:
                self._cache_repo.add(user_id, recomm)

            i += 1

        self._cache_repo.commit()
        logger.info('Calculation done')
