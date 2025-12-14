from uuid import uuid4

from entity.group import Group
from entity.parameters import Parameters, Sex, UserType
from entity.point import Point
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

    def _make_avg_group(self):
        rooms, roommates, month, budget, geo_lat, geo_lon, age = (
            self._group_repo.get_avg_params()
        )
        avg_group = Group(
            owner_id=uuid4(),
            max_users=roommates + 1,
            parameters=Parameters(
                geo=Point(lat=geo_lat, lon=geo_lon),
                budget=budget,
                room_count=rooms,
                roommates_count=roommates,
                age=age,
                month=month,
                name='AvgGroup',
                surname='AvgGroup',
                photos=[''],
                address='',
                smoking=False,
                alko=False,
                pet=False,
                description='AvgGroup',
                sex=Sex.MALE,
                user_type=UserType.STUDENT,
            ),
        )
        group_id = self._group_repo.create(avg_group)
        logger.debug(f'Avg group {avg_group.to_dict()}')
        recomm = self._rec_repo.execute(group_id)
        logger.debug(f'Avg group recs {recomm}')
        self._cache_repo.add_default(recomm)
        self._cache_repo.commit()
        self._group_repo.delete(group_id)
        logger.debug(f'Delete avg group {group_id}')

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

        logger.info('Calculating avg group')
        self._make_avg_group()

        self._cache_repo.commit()
        logger.info('Calculation done')
