import pytest
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import Organization, User
from apps.logistics.realtime import fleet_group
from config.asgi import application

pytestmark = [pytest.mark.asyncio, pytest.mark.django_db(transaction=True)]


@database_sync_to_async
def login_as(role, slug="alfa", with_org=True):
    """Cria usuário (e a empresa, se preciso) e devolve (access token, id da empresa)."""
    org = Organization.objects.get_or_create(slug=slug, defaults={"name": slug})[0] if with_org else None
    user = User.objects.create_user(
        email=f"{role.lower()}@{slug}.ws", password="x", role=role, organization=org, is_email_verified=True
    )
    return str(AccessToken.for_user(user)), (org.id if org else None)


def communicator(token=None):
    query = f"?token={token}" if token else ""
    return WebsocketCommunicator(application, f"/ws/fleet/{query}", headers=[(b"origin", b"http://localhost")])


async def test_manager_receives_positions_of_own_company():
    token, org_id = await login_as("MANAGER")
    comm = communicator(token)
    connected, _ = await comm.connect()
    assert connected

    payload = {"plate": "ABC1D23", "speed_kmh": 72}
    await get_channel_layer().group_send(fleet_group(org_id), {"type": "fleet.position", "payload": payload})
    assert await comm.receive_json_from() == payload
    await comm.disconnect()


async def test_manager_never_receives_positions_of_another_company():
    token, _ = await login_as("MANAGER", slug="alfa")
    _, other_org_id = await login_as("MANAGER", slug="beta")
    comm = communicator(token)
    assert (await comm.connect())[0]

    await get_channel_layer().group_send(fleet_group(other_org_id), {"type": "fleet.position", "payload": {"plate": "VAZOU"}})
    assert await comm.receive_nothing() is True  # nada chega: grupos separados por empresa
    await comm.disconnect()


async def test_driver_and_companyless_users_are_rejected():
    driver_token, _ = await login_as("DRIVER")
    assert not (await communicator(driver_token).connect())[0]
    orphan_token, _ = await login_as("MANAGER", slug="sem-empresa", with_org=False)
    assert not (await communicator(orphan_token).connect())[0]


async def test_missing_or_invalid_token_is_rejected():
    assert not (await communicator().connect())[0]
    assert not (await communicator("token-invalido").connect())[0]
