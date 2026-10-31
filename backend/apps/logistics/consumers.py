from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .realtime import fleet_group


class FleetConsumer(AsyncJsonWebsocketConsumer):
    """Stream de posições da frota da empresa do usuário. Somente gestores/admin."""

    group = None

    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return
        if user.role not in ("ADMIN", "MANAGER") or not user.organization_id:
            await self.close(code=4403)
            return
        self.group = fleet_group(user.organization_id)
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if self.group:
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def fleet_position(self, event):
        await self.send_json(event["payload"])
