from django.db.models import ProtectedError
from rest_framework.response import Response
from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    if isinstance(exc, ProtectedError):
        return Response(
            {"detail": "Não é possível excluir: há registros vinculados (ex.: viagens). Marque o item como inativo."},
            status=409,
        )
    return exception_handler(exc, context)
