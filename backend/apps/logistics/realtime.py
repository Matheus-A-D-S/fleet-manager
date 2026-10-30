import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)

FLEET_GROUP = "fleet"


def live_payload(ping):
    """Formato único da posição de um veículo (usado pelo endpoint /live/ e pelo WebSocket)."""
    return {
        "vehicle_id": ping.vehicle_id,
        "plate": ping.vehicle.plate,
        "vehicle_status": ping.vehicle.status,
        "trip_id": ping.trip_id,
        "trip_code": ping.trip.code if ping.trip else None,
        "latitude": ping.latitude,
        "longitude": ping.longitude,
        "speed_kmh": ping.speed_kmh,
        "heading": ping.heading,
        "recorded_at": ping.recorded_at.isoformat(),
    }


def publish_position(ping):
    """Envia a posição aos gestores conectados. Falha aqui nunca pode derrubar a ingestão do GPS."""
    try:
        layer = get_channel_layer()
        if layer is not None:
            async_to_sync(layer.group_send)(FLEET_GROUP, {"type": "fleet.position", "payload": live_payload(ping)})
    except Exception:
        logger.warning("Falha ao publicar posição em tempo real", exc_info=True)
