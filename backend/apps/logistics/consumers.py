from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .realtime import FLEET_GROUP


class FleetConsumer(AsyncJsonWebsocketConsumer):
    """Stream de posições da frota. Somente gestores/admin."""

    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return
        if user.role not in ("ADMIN", "MANAGER"):
            await self.close(code=4403)
            return
        await self.channel_layer.group_add(FLEET_GROUP, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(FLEET_GROUP, self.channel_name)

    async def fleet_position(self, event):
        await self.send_json(event["payload"])
