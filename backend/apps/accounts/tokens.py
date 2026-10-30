from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import signing
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

VERIFY_SALT = "accounts.verify-email"
VERIFY_MAX_AGE = 60 * 60 * 48  # 48h


def make_verification_token(user):
    """Token assinado (stateless) para confirmar o e-mail."""
    return signing.dumps({"uid": user.pk, "email": user.email}, salt=VERIFY_SALT)


def read_verification_token(token):
    """Levanta signing.BadSignature / SignatureExpired se inválido ou expirado."""
    return signing.loads(token, salt=VERIFY_SALT, max_age=VERIFY_MAX_AGE)


def make_reset_params(user):
    """uid + token de redefinição. O token se invalida sozinho quando a senha muda."""
    return urlsafe_base64_encode(force_bytes(user.pk)), default_token_generator.make_token(user)


def get_user_from_reset(uidb64, token):
    User = get_user_model()
    try:
        user = User.objects.get(pk=force_str(urlsafe_base64_decode(uidb64)), is_active=True)
    except (User.DoesNotExist, ValueError, TypeError, OverflowError):
        return None
    return user if default_token_generator.check_token(user, token) else None
