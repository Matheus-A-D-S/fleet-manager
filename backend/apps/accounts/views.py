from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core import signing
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import generics, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from apps.audit.models import AuditLog
from apps.audit.services import diff, record
from apps.core.tenancy import TenantQuerysetMixin

from .permissions import IsManager, IsOrgAdmin
from .serializers import (
    EmailSerializer,
    EmailTokenObtainPairSerializer,
    LogoutSerializer,
    PasswordResetConfirmSerializer,
    RegisterSerializer,
    UserInviteSerializer,
    UserSerializer,
    UserUpdateSerializer,
    VerifyEmailSerializer,
)
from .tasks import send_invitation_email, send_password_reset_email, send_verification_email
from .tokens import get_user_from_reset, read_verification_token

User = get_user_model()


class LoginView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer


class RegisterView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

    def perform_create(self, serializer):
        user = serializer.save()
        transaction.on_commit(lambda: send_verification_email.delay(user.pk))


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        s = VerifyEmailSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        try:
            data = read_verification_token(s.validated_data["token"])
        except signing.SignatureExpired:
            return Response({"detail": "Link expirado. Solicite um novo e-mail de confirmação."}, status=400)
        except signing.BadSignature:
            return Response({"detail": "Link inválido."}, status=400)
        user = User.objects.filter(pk=data["uid"], email=data["email"]).first()
        if not user:
            return Response({"detail": "Link inválido."}, status=400)
        if not user.is_email_verified:  # idempotente
            user.is_email_verified = True
            user.save(update_fields=["is_email_verified"])
        return Response({"detail": "E-mail confirmado. Você já pode entrar."})


class ResendVerificationView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        s = EmailSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = User.objects.filter(email__iexact=s.validated_data["email"], is_email_verified=False).first()
        if user:
            send_verification_email.delay(user.pk)
        # Resposta idêntica exista ou não a conta (evita enumeração de usuários).
        return Response({"detail": "Se a conta existir, enviamos um novo e-mail de confirmação."})


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        s = EmailSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = User.objects.filter(email__iexact=s.validated_data["email"], is_active=True).first()
        if user:
            send_password_reset_email.delay(user.pk)
        return Response({"detail": "Se a conta existir, enviamos as instruções por e-mail."})


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        s = PasswordResetConfirmSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = get_user_from_reset(s.validated_data["uid"], s.validated_data["token"])
        if not user:
            return Response({"detail": "Link inválido ou expirado."}, status=400)
        try:
            validate_password(s.validated_data["password"], user)
        except DjangoValidationError as exc:
            return Response({"password": list(exc.messages)}, status=400)
        user.set_password(s.validated_data["password"])
        user.is_email_verified = True  # quem recebeu o e-mail provou controlar a caixa
        user.save()
        return Response({"detail": "Senha alterada com sucesso."})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        s = LogoutSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        try:
            RefreshToken(s.validated_data["refresh"]).blacklist()
        except TokenError:
            pass
        return Response(status=status.HTTP_205_RESET_CONTENT)


class MeView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]  # superusuário da plataforma (sem empresa) também consulta o próprio perfil
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


def _user_state(user):
    return {"first_name": user.first_name, "last_name": user.last_name, "role": user.role, "is_active": user.is_active}


class UserViewSet(
    TenantQuerysetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Equipe da empresa. Gestores consultam; só o administrador convida e edita. Não há exclusão: desative."""

    queryset = User.objects.select_related("organization")
    filterset_fields = ["role", "is_active"]
    search_fields = ["email", "first_name", "last_name"]
    ordering_fields = ["email", "first_name"]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsManager()]
        return [IsOrgAdmin()]

    def get_serializer_class(self):
        if self.action == "create":
            return UserInviteSerializer
        if self.action in ("update", "partial_update"):
            return UserUpdateSerializer
        return UserSerializer

    def perform_create(self, serializer):
        user = serializer.save(organization=self.request.user.organization)
        # Não usamos snapshot() aqui: o modelo de usuário contém o hash da senha.
        record(self.request, AuditLog.Action.CREATE, user, {"email": user.email, **_user_state(user)})
        inviter_id = self.request.user.pk
        transaction.on_commit(lambda: send_invitation_email.delay(user.pk, inviter_id))

    def perform_update(self, serializer):
        before = _user_state(serializer.instance)
        user = serializer.save()
        record(self.request, AuditLog.Action.UPDATE, user, diff(before, _user_state(user)))

    @action(detail=True, methods=["post"], url_path="resend-invite")
    def resend_invite(self, request, pk=None):
        user = self.get_object()
        if user.is_email_verified or not user.is_active:
            raise ValidationError({"detail": "Este usuário já ativou a conta ou está desativado."})
        send_invitation_email.delay(user.pk, request.user.pk)
        return Response({"detail": "Convite reenviado."})
