from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail

from .tokens import make_reset_params, make_verification_token


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_verification_email(user_id):
    user = get_user_model().objects.filter(pk=user_id).first()
    if not user or user.is_email_verified:
        return
    link = f"{settings.FRONTEND_URL}/verify-email?token={make_verification_token(user)}"
    send_mail(
        subject="Confirme seu e-mail - FleetTrack",
        message=(
            f"Olá, {user.first_name or user.email}!\n\n"
            f"Para ativar sua conta, confirme seu e-mail:\n{link}\n\n"
            "O link expira em 48 horas. Se você não criou esta conta, ignore esta mensagem."
        ),
        from_email=None,
        recipient_list=[user.email],
    )


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_password_reset_email(user_id):
    user = get_user_model().objects.filter(pk=user_id, is_active=True).first()
    if not user:
        return
    uid, token = make_reset_params(user)
    link = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"
    send_mail(
        subject="Redefinição de senha - FleetTrack",
        message=(
            f"Recebemos um pedido para redefinir sua senha.\n\n{link}\n\n"
            "Se não foi você, ignore esta mensagem: sua senha continua a mesma."
        ),
        from_email=None,
        recipient_list=[user.email],
    )


@shared_task(autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def send_invitation_email(user_id, invited_by_id=None):
    User = get_user_model()
    user = User.objects.filter(pk=user_id, is_active=True).select_related("organization").first()
    if not user or user.is_email_verified:  # já ativou a conta
        return
    inviter = User.objects.filter(pk=invited_by_id).first() if invited_by_id else None
    who = (inviter.first_name or inviter.email) if inviter else "Um administrador"
    company = user.organization.name if user.organization else "sua empresa"
    uid, token = make_reset_params(user)
    link = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"
    send_mail(
        subject=f"Convite para a equipe {company} no FleetTrack",
        message=(
            f"{who} convidou você para a equipe {company} no FleetTrack, com o perfil {user.get_role_display()}.\n\n"
            f"Defina sua senha e entre:\n{link}\n\n"
            "O link expira em 3 dias. Se você não esperava este convite, ignore esta mensagem."
        ),
        from_email=None,
        recipient_list=[user.email],
    )
