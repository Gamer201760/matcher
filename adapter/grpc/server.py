from uuid import UUID

import grpc
from google.protobuf.empty_pb2 import Empty

import gen.matcher.matcher_pb2 as pb2
import gen.matcher.matcher_pb2_grpc as pb2_grpc
from entity.errors import DomainError, NotFoundError
from usecase.form import FormService
from usecase.group import (
    FindGroupService,
    GroupService,
)
from usecase.group_query import GroupQuery

from .mapper import (
    from_proto_parameters,
    to_proto_form,
    to_proto_group,
    to_proto_group_with_score,
    to_proto_request,
)


class FormServicer(pb2_grpc.FormServiceServicer):
    def __init__(self, service: FormService):
        self.service = service

    def CreateForm(self, request, context):
        try:
            user_id = UUID(request.user_id)
            parameters = from_proto_parameters(request.parameters)
            self.service.create(user_id, parameters)
            return Empty()
        except NotFoundError as e:
            context.abort(grpc.StatusCode.NOT_FOUND, str(e))
        except DomainError as e:
            context.abort(grpc.StatusCode.FAILED_PRECONDITION, str(e))
        except Exception as e:
            context.abort(grpc.StatusCode.INTERNAL, f'Internal error: {str(e)}')

    def GetFormByUser(self, request, context):
        try:
            user_id = UUID(request.user_id)
            form = self.service.get_by_user(user_id)
            return to_proto_form(form)
        except NotFoundError as e:
            context.abort(grpc.StatusCode.NOT_FOUND, str(e))
        except Exception as e:
            context.abort(grpc.StatusCode.INTERNAL, f'Internal error: {str(e)}')

    def UpdateForm(self, request, context):
        try:
            user_id = UUID(request.user_id)
            parameters = from_proto_parameters(request.parameters)
            self.service.update(user_id, parameters)
            return Empty()
        except NotFoundError as e:
            context.abort(grpc.StatusCode.NOT_FOUND, str(e))
        except DomainError as e:
            context.abort(grpc.StatusCode.FAILED_PRECONDITION, str(e))
        except Exception as e:
            context.abort(grpc.StatusCode.INTERNAL, f'Internal error: {str(e)}')

    def DeleteForm(self, request, context):
        try:
            user_id = UUID(request.user_id)
            self.service.delete(user_id)
            return Empty()
        except NotFoundError as e:
            context.abort(grpc.StatusCode.NOT_FOUND, str(e))
        except DomainError as e:
            context.abort(grpc.StatusCode.FAILED_PRECONDITION, str(e))
        except Exception as e:
            context.abort(grpc.StatusCode.INTERNAL, f'Internal error: {str(e)}')


class GroupQueryServicer(pb2_grpc.GroupQueryServiceServicer):
    def __init__(self, query: GroupQuery):
        self.query = query

    def GetGroup(self, request, context):
        try:
            group_id = UUID(request.group_id)
            group = self.query.get(group_id)
            return to_proto_group(group)
        except NotFoundError as e:
            context.abort(grpc.StatusCode.NOT_FOUND, str(e))
        except Exception as e:
            context.abort(grpc.StatusCode.INTERNAL, f'Internal error: {str(e)}')

    def DeleteGroup(self, request, context):
        try:
            owner_id = UUID(request.owner_id)
            self.query.delete(owner_id)
            return Empty()
        except NotFoundError as e:
            context.abort(grpc.StatusCode.NOT_FOUND, str(e))
        except DomainError as e:
            context.abort(grpc.StatusCode.FAILED_PRECONDITION, str(e))
        except Exception as e:
            context.abort(grpc.StatusCode.INTERNAL, f'Internal error: {str(e)}')

    def ListGroupMembers(self, request, context):
        try:
            group_id = UUID(request.group_id)
            members = self.query.list_members(group_id)
            return pb2.ListGroupMembersResponse(
                members=[to_proto_form(m) for m in members]
            )
        except NotFoundError as e:
            context.abort(grpc.StatusCode.NOT_FOUND, str(e))
        except Exception as e:
            context.abort(grpc.StatusCode.INTERNAL, f'Internal error: {str(e)}')


class FindGroupServicer(pb2_grpc.FindGroupServiceServicer):
    def __init__(self, service: FindGroupService):
        self.service = service

    def FindGroups(self, request, context):
        try:
            user_id = UUID(request.user_id)
            groups = self.service.execute(user_id)
            return pb2.FindGroupsResponse(
                groups=[to_proto_group_with_score(g[0], g[1]) for g in groups]
            )
        except NotFoundError as e:
            context.abort(grpc.StatusCode.NOT_FOUND, str(e))
        except DomainError as e:
            context.abort(grpc.StatusCode.FAILED_PRECONDITION, str(e))
        except Exception as e:
            context.abort(grpc.StatusCode.INTERNAL, f'Internal error: {str(e)}')


class GroupServicer(pb2_grpc.GroupServiceServicer):
    def __init__(self, service: GroupService):
        self.service = service

    def GetReqeusts(self, request: pb2.GetReqeustsRequest, context):
        try:
            group_id = UUID(request.group_id)
            requests = self.service.get_requests(group_id)
            return pb2.GetReqeustsResponse(
                requests=[to_proto_request(r) for r in requests]
            )
        except NotFoundError as e:
            context.abort(grpc.StatusCode.NOT_FOUND, str(e))
        except DomainError as e:
            context.abort(grpc.StatusCode.FAILED_PRECONDITION, str(e))
        except Exception as e:
            context.abort(grpc.StatusCode.INTERNAL, f'Internal error: {str(e)}')

    def SendJoinRequest(self, request, context):
        try:
            user_id = UUID(request.user_id)
            group_id = UUID(request.group_id)
            self.service.send_join_request(user_id, group_id)
            return Empty()
        except NotFoundError as e:
            context.abort(grpc.StatusCode.NOT_FOUND, str(e))
        except DomainError as e:
            context.abort(grpc.StatusCode.FAILED_PRECONDITION, str(e))
        except Exception as e:
            context.abort(grpc.StatusCode.INTERNAL, f'Internal error: {str(e)}')

    def AcceptJoinRequest(self, request, context):
        try:
            owner_id = UUID(request.owner_id)
            request_id = UUID(request.request_id)
            self.service.accept_join_request(owner_id, request_id)
            return Empty()
        except NotFoundError as e:
            context.abort(grpc.StatusCode.NOT_FOUND, str(e))
        except DomainError as e:
            context.abort(grpc.StatusCode.FAILED_PRECONDITION, str(e))
        except Exception as e:
            context.abort(grpc.StatusCode.INTERNAL, f'Internal error: {str(e)}')

    def RejectJoinRequest(self, request, context):
        try:
            owner_id = UUID(request.owner_id)
            request_id = UUID(request.request_id)
            self.service.reject_join_request(owner_id, request_id)
            return Empty()
        except NotFoundError as e:
            context.abort(grpc.StatusCode.NOT_FOUND, str(e))
        except DomainError as e:
            context.abort(grpc.StatusCode.FAILED_PRECONDITION, str(e))
        except Exception as e:
            context.abort(grpc.StatusCode.INTERNAL, f'Internal error: {str(e)}')
