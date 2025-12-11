from uuid import UUID

from kafka import KafkaProducer

from entity.group import Group, GroupRequest


class MockNotificationRepository:
    """
    Топики:
      matcher.group.join-request
      matcher.group.accept
      matcher.group.reject
      matcher.group.kick
      matcher.group.leave
    """

    def send_join_request(self, group: 'Group', user_id: UUID) -> None:
        print('Send event', group, user_id)

    def accept_join_request(self, group: 'Group', request: 'GroupRequest') -> None:
        print('accept_join_request', group, request)

    def reject_join_request(self, group: 'Group', request: 'GroupRequest') -> None:
        print('reject_join_request', group, request)

    def kick(self, group: 'Group', user_id: UUID, remained: int) -> None:
        print('kick', group, remained, user_id)

    def leave(self, group: 'Group', user_id: UUID, remained: int) -> None:
        print('leave', group, remained, user_id)

    def flush(self) -> None: ...


class KafkaNotificationRepository:
    """
    Топики:
      matcher.group.join-request
      matcher.group.accept
      matcher.group.reject
      matcher.group.kick
      matcher.group.leave
    """

    def __init__(self, producer: KafkaProducer) -> None:
        self._producer = producer

    def _send(self, topic: str, payload: dict) -> None:
        self._producer.send(topic, value=payload)

    @staticmethod
    def _group_to_dict(group: Group) -> dict:
        return group.to_dict()

    @staticmethod
    def _request_to_dict(request: GroupRequest) -> dict:
        return request.to_dict()

    def send_join_request(self, group: 'Group', user_id: UUID) -> None:
        topic = 'matcher.group.join-request'
        payload = {
            'event': 'join_request',
            'group': self._group_to_dict(group),
            'user_id': str(user_id),
        }
        self._send(topic, payload)

    def accept_join_request(self, group: 'Group', request: 'GroupRequest') -> None:
        topic = 'matcher.group.accept'
        payload = {
            'event': 'join_accept',
            'group': self._group_to_dict(group),
            'request': self._request_to_dict(request),
        }
        self._send(topic, payload)

    def reject_join_request(self, group: 'Group', request: 'GroupRequest') -> None:
        topic = 'matcher.group.reject'
        payload = {
            'event': 'join_reject',
            'group': self._group_to_dict(group),
            'request': self._request_to_dict(request),
        }
        self._send(topic, payload)

    def kick(self, group: 'Group', user_id: UUID, remained: int) -> None:
        topic = 'matcher.group.kick'
        payload = {
            'event': 'kick',
            'group': self._group_to_dict(group),
            'user_id': str(user_id),
            'remained': remained,
        }
        self._send(topic, payload)

    def leave(self, group: 'Group', user_id: UUID, remained: int) -> None:
        topic = 'matcher.group.leave'
        payload = {
            'event': 'leave',
            'group': self._group_to_dict(group),
            'user_id': str(user_id),
            'remained': remained,
        }
        self._send(topic, payload)

    def flush(self) -> None:
        self._producer.flush()
