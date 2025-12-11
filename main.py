import os
from concurrent import futures

import grpc
from dotenv import load_dotenv
from grpc_reflection.v1alpha import reflection

import gen.matcher.matcher_pb2 as pb2
import gen.matcher.matcher_pb2_grpc as pb2_grpc
from adapter.grpc.server import (
    FindGroupServicer,
    FormServicer,
    GroupQueryServicer,
    GroupServicer,
)
from infrastructure.config import PARAMETERS
from infrastructure.logging_utils import setup_logger
from infrastructure.neo4j.connection import ensure_constraints_and_index, get_driver
from repository.form_repository import FormRepository
from repository.group_recommendation_repository import GroupRecommendationRepository
from repository.group_repository import GroupRepository
from repository.group_request_in_memory import InMemoryGroupRequestRepository
from repository.notify_repository import MockNotificationRepository
from usecase.form import FormService
from usecase.group import FindGroupService, GroupService
from usecase.group_query import GroupQuery

logger = setup_logger('main')

load_dotenv()


def main():
    logger.info('start')
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    driver = get_driver(
        os.getenv('NEO4J_URI', ''),
        os.getenv('NEO4J_USERNAME', ''),
        os.getenv('NEO4J_PASSWORD', ''),
    )
    with driver.session() as session:
        ensure_constraints_and_index(session, dims=len(PARAMETERS))

    # producer = KafkaProducer(
    #     bootstrap_servers=os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092'),
    #     value_serializer=lambda v: json.dumps(v).encode('utf-8'),
    # )
    # notify_repo = KafkaNotificationRepository(producer)
    notify_repo = MockNotificationRepository()

    group_repo = GroupRepository(driver)
    recomend_repo = GroupRecommendationRepository(driver)
    form_repo = FormRepository(driver)
    # req_repo = GroupRequestRepository(driver)
    req_repo = InMemoryGroupRequestRepository()

    form_serv = FormService(form_repo, group_repo)
    find_serv = FindGroupService(
        group_repo,
        recomend_repo,
    )
    group_serv = GroupService(group_repo, req_repo, notify_repo)

    group_q = GroupQuery(group_repo, form_repo, notify_repo)

    # Регистрация сервиса
    pb2_grpc.add_FindGroupServiceServicer_to_server(
        FindGroupServicer(find_serv),
        server,
    )
    pb2_grpc.add_FormServiceServicer_to_server(FormServicer(form_serv), server)
    pb2_grpc.add_GroupQueryServiceServicer_to_server(
        GroupQueryServicer(group_q), server
    )
    pb2_grpc.add_GroupServiceServicer_to_server(GroupServicer(group_serv), server)

    service_names = tuple(
        s.full_name for s in pb2.DESCRIPTOR.services_by_name.values()
    ) + (reflection.SERVICE_NAME,)
    reflection.enable_server_reflection(service_names, server)

    # Привязка к порту
    server.add_insecure_port('0.0.0.0:50051')

    # Запуск сервера
    server.start()
    logger.info('gRPC server started on port 50051')

    # Ожидание завершения
    server.wait_for_termination()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info('Goodbye!')
