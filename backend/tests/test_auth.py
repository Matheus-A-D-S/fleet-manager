import pytest
from django.core import mail

from apps.accounts.models import Organization, User
from conftest import PASSWORD, link_params

pytestmark = pytest.mark.django_db(transaction=True)


def test_register_verify_and_login_flow(api):
    data = {"email": "novo@test.com", "password": PASSWORD, "first_name": "Novo", "company_name": "Nova Frota Ltda"}
    assert api.post("/api/auth/register/", data, format="json").status_code == 201

    user = User.objects.get(email="novo@test.com")
    assert not user.is_email_verified
    assert user.role == "ADMIN" and user.organization.name == "Nova Frota Ltda"  # cria a empresa e o 1º admin
    assert len(mail.outbox) == 1

    # sem confirmar o e-mail, o login é bloqueado
    login = {"email": "novo@test.com", "password": PASSWORD}
    assert api.post("/api/auth/login/", login, format="json").status_code == 403

    token = link_params(mail.outbox[0].body, "verify-email")["token"]
    assert api.post("/api/auth/verify-email/", {"token": token}, format="json").status_code == 200
    assert api.post("/api/auth/verify-email/", {"token": token}, format="json").status_code == 200  # idempotente

    response = api.post("/api/auth/login/", login, format="json")
    assert response.status_code == 200
    assert {"access", "refresh", "user"} <= response.data.keys()


def test_register_rejects_weak_password_and_duplicate_email(api, manager):
    weak = {"email": "x@test.com", "password": "123", "first_name": "X", "company_name": "X"}
    assert api.post("/api/auth/register/", weak, format="json").status_code == 400
    dup = {"email": manager.email, "password": PASSWORD, "first_name": "X", "company_name": "X"}
    assert api.post("/api/auth/register/", dup, format="json").status_code == 400


def test_invalid_verification_token_is_rejected(api):
    assert api.post("/api/auth/verify-email/", {"token": "lixo"}, format="json").status_code == 400


def test_wrong_password_returns_401(api, manager):
    response = api.post("/api/auth/login/", {"email": manager.email, "password": "errada"}, format="json")
    assert response.status_code == 401


def test_password_reset_flow(api, manager):
    assert api.post("/api/auth/password-reset/", {"email": manager.email}, format="json").status_code == 200
    params = link_params(mail.outbox[0].body, "reset-password")

    payload = {**params, "password": "NovaSenha@2026"}
    assert api.post("/api/auth/password-reset/confirm/", payload, format="json").status_code == 200
    # o mesmo link não funciona duas vezes: o token se invalida quando a senha muda
    assert api.post("/api/auth/password-reset/confirm/", payload, format="json").status_code == 400

    login = {"email": manager.email, "password": "NovaSenha@2026"}
    assert api.post("/api/auth/login/", login, format="json").status_code == 200


def test_password_reset_does_not_reveal_unknown_accounts(api):
    response = api.post("/api/auth/password-reset/", {"email": "ninguem@test.com"}, format="json")
    assert response.status_code == 200
    assert mail.outbox == []


def test_logout_blacklists_refresh_token(api, manager):
    tokens = api.post("/api/auth/login/", {"email": manager.email, "password": PASSWORD}, format="json").data
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
    assert api.post("/api/auth/logout/", {"refresh": tokens["refresh"]}, format="json").status_code == 205
    api.credentials()
    assert api.post("/api/auth/token/refresh/", {"refresh": tokens["refresh"]}, format="json").status_code == 401


def test_unverified_users_never_get_tokens(api):
    User.objects.create_user(email="pendente@test.com", password=PASSWORD)
    response = api.post("/api/auth/login/", {"email": "pendente@test.com", "password": PASSWORD}, format="json")
    assert response.status_code == 403
    assert "access" not in response.data


def test_registration_requires_company_name(api):
    response = api.post("/api/auth/register/", {"email": "x@test.com", "password": PASSWORD, "first_name": "X"}, format="json")
    assert response.status_code == 400 and "company_name" in response.data


def test_companies_with_the_same_name_get_distinct_slugs(api):
    for email in ("a@test.com", "b@test.com"):
        data = {"email": email, "password": PASSWORD, "first_name": "X", "company_name": "Frota Norte"}
        assert api.post("/api/auth/register/", data, format="json").status_code == 201
    slugs = sorted(Organization.objects.values_list("slug", flat=True))
    assert slugs == ["frota-norte", "frota-norte-2"]
