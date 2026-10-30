from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ObjectDoesNotExist
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken


@database_sync_to_async
def _user_from_token(token):
    try:
        payload = AccessToken(token)  # valida assinatura, tipo e expiração
        return get_user_model().objects.get(pk=payload["user_id"], is_active=True)
    except (TokenError, KeyError, ObjectDoesNotExist):
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """Autentica a conexão WebSocket com o access token (?token=...). Ver docs/DECISIONS.md (ADR-005)."""

    async def __call__(self, scope, receive, send):
        token = (parse_qs(scope.get("query_string", b"").decode()).get("token") or [None])[0]
        scope["user"] = await _user_from_token(token) if token else AnonymousUser()
        return await super().__call__(scope, receive, send)
