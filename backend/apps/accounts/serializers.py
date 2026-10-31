from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import APIException
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import Organization

User = get_user_model()


class EmailNotVerified(APIException):
    status_code = 403
    default_detail = "E-mail ainda não confirmado. Use o link enviado à sua caixa de entrada."
    default_code = "email_not_verified"


class UserSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source="get_role_display", read_only=True)
    organization_name = serializers.CharField(source="organization.name", read_only=True, default=None)

    class Meta:
        model = User
        fields = [
            "id", "email", "first_name", "last_name", "role", "role_display",
            "is_active", "is_email_verified", "organization", "organization_name",
        ]
        read_only_fields = fields


class RegisterSerializer(serializers.ModelSerializer):
    """Cadastro público: cria a EMPRESA e o primeiro administrador dela."""

    password = serializers.CharField(write_only=True)
    company_name = serializers.CharField(write_only=True, max_length=120)

    class Meta:
        model = User
        fields = ["email", "password", "first_name", "last_name", "company_name"]

    def validate_email(self, value):
        value = value.lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Já existe uma conta com este e-mail.")
        return value

    def validate(self, attrs):
        validate_password(attrs["password"], User(email=attrs["email"]))
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        company_name = validated_data.pop("company_name")
        organization = Organization.objects.create_with_unique_slug(company_name)
        return User.objects.create_user(role=User.Role.ADMIN, organization=organization, **validated_data)


class UserInviteSerializer(serializers.ModelSerializer):
    """Convite de um novo usuário para a empresa do administrador (sem senha: ele define pelo e-mail)."""

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "role"]
        read_only_fields = ["id"]

    def validate_email(self, value):
        value = value.lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Este e-mail já está cadastrado.")
        return value

    def create(self, validated_data):
        return User.objects.create_user(password=None, **validated_data)


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "role", "is_active"]

    def validate(self, attrs):
        me = self.context["request"].user
        if self.instance and self.instance.pk == me.pk:  # evita que a empresa fique sem administrador
            if "role" in attrs and attrs["role"] != self.instance.role:
                raise serializers.ValidationError({"role": "Você não pode alterar o seu próprio perfil."})
            if attrs.get("is_active") is False:
                raise serializers.ValidationError({"is_active": "Você não pode desativar a si mesmo."})
        return attrs


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["org"] = user.organization_id
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        if not self.user.is_email_verified:
            raise EmailNotVerified()
        data["user"] = UserSerializer(self.user).data
        return data


class EmailSerializer(serializers.Serializer):
    email = serializers.EmailField()


class VerifyEmailSerializer(serializers.Serializer):
    token = serializers.CharField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    password = serializers.CharField(write_only=True)


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()
