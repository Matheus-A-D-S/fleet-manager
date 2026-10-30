import pytest
from channels.db import database_sync_to_async
from channels.layers import get_channel_layer
from channels.testing import WebsocketCommunicator
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import User
from config.asgi import application

pytestmark = [pytest.mark.asyncio, pytest.mark.django_db(transaction=True)]


@database_sync_to_async
def token_for(role):
    user = User.objects.create_user(email=f"{role.lower()}@ws.test", password="x", role=role, is_email_verified=True)
    return str(AccessToken.for_user(user))


def communicator(token=None):
    query = f"?token={token}" if token else ""
    return WebsocketCommunicator(application, f"/ws/fleet/{query}", headers=[(b"origin", b"http://localhost")])


async def test_manager_receives_broadcast_positions():
    comm = communicator(await token_for("MANAGER"))
    connected, _ = await comm.connect()
    assert connected

    await get_channel_layer().group_send("fleet", {"type": "fleet.position", "payload": {"plate": "ABC1D23", "speed_kmh": 72}})
    assert await comm.receive_json_from() == {"plate": "ABC1D23", "speed_kmh": 72}
    await comm.disconnect()


async def test_driver_is_rejected():
    connected, _ = await communicator(await token_for("DRIVER")).connect()
    assert not connected


async def test_missing_or_invalid_token_is_rejected():
    assert not (await communicator().connect())[0]
    assert not (await communicator("token-invalido").connect())[0]
