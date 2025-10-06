from uuid import UUID

import grpc
from google.protobuf import empty_pb2

from adapter.grpc import mapper
from entity.errors import EntityAlreadyExistsError, NotFoundError
from gen.form import form_pb2
from gen.form.form_pb2_grpc import FormServiceStub
from usecase.form_query import FormQuery


class FormServiceAdapter(FormServiceStub):
    """
    Адаптер, который связывает gRPC-интерфейс с бизнес-логикой (FormQuery).
    """

    def __init__(self, query_service: FormQuery):
        self.query_service = query_service

    def CreateForm(self, request: form_pb2.CreateFormRequest, context):
        try:
            domain_form = mapper.proto_to_domain(request.form)
            self.query_service.create_form(domain_form)
            return empty_pb2.Empty()
        except EntityAlreadyExistsError as e:
            context.set_code(grpc.StatusCode.ALREADY_EXISTS)
            context.set_details(str(e))
            return empty_pb2.Empty()
        except Exception as e:
            # Общая обработка непредвиденных ошибок
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f'An internal error occurred: {e}')
            return empty_pb2.Empty()

    def GetForm(self, request: form_pb2.GetFormRequest, context):
        try:
            user_id = UUID(request.user_id)
            domain_form = self.query_service.get_form(user_id)
            return mapper.domain_to_proto(domain_form)
        except NotFoundError as e:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(str(e))
            # При ошибке возвращаем пустой объект, как того требует сигнатура RPC
            return form_pb2.Form()
        except ValueError:
            # Если передан невалидный UUID
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(f"Invalid user_id format: '{request.user_id}'")
            return form_pb2.Form()
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f'An internal error occurred: {e}')
            return form_pb2.Form()

    def UpdateForm(self, request: form_pb2.UpdateFormRequest, context):
        try:
            domain_form = mapper.proto_to_domain(request.form)
            self.query_service.update_form(domain_form)
            return empty_pb2.Empty()
        except NotFoundError as e:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(str(e))
            return empty_pb2.Empty()
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f'An internal error occurred: {e}')
            return empty_pb2.Empty()

    def DeleteForm(self, request: form_pb2.DeleteFormRequest, context):
        try:
            user_id = UUID(request.user_id)
            self.query_service.delete_form(user_id)
            return empty_pb2.Empty()
        except NotFoundError as e:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(str(e))
            return empty_pb2.Empty()
        except ValueError:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(f"Invalid user_id format: '{request.user_id}'")
            return empty_pb2.Empty()
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f'An internal error occurred: {e}')
            return empty_pb2.Empty()
