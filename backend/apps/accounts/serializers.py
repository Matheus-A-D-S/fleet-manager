from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.exceptions import APIException
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class EmailNotVerified(APIException):
    status_code = 403
    default_detail = "E-mail ainda não confirmado. Use o link enviado à sua caixa de entrada."
    default_code = "email_not_verified"


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "role", "is_email_verified"]
        read_only_fields = fields


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["email", "password", "first_name", "last_name"]

    def validate_email(self, value):
        value = value.lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Já existe uma conta com este e-mail.")
        return value

    def validate(self, attrs):
        validate_password(attrs["password"], User(email=attrs["email"]))
        return attrs

    def create(self, validated_data):
        # Cadastro público sempre cria MOTORISTA; promoção de perfil é feita por um admin.
        return User.objects.create_user(role=User.Role.DRIVER, **validated_data)


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
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
