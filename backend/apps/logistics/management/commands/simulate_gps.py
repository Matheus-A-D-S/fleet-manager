import random
import time

from django.core.management.base import BaseCommand

from apps.alerts import services as alert_services
from apps.logistics import realtime
from apps.logistics.models import LocationPing, Trip

DEFAULT_START = (-8.76, -63.90)


class Command(BaseCommand):
    help = "Simula o GPS dos veículos com viagem em andamento (demonstração do mapa em tempo real)."

    def add_arguments(self, parser):
        parser.add_argument("--interval", type=float, default=2.0, help="segundos entre os envios")
        parser.add_argument("--speeding", action="store_true", help="inclui picos de velocidade para testar alertas")

    def handle(self, *args, **opts):
        trips = list(Trip.objects.filter(status=Trip.Status.IN_PROGRESS).select_related("vehicle"))
        if not trips:
            self.stderr.write("Nenhuma viagem em andamento. Rode seed_demo ou inicie uma viagem pela tela.")
            return

        positions = {}
        for trip in trips:
            last = trip.pings.order_by("-recorded_at").first()
            positions[trip.pk] = (last.latitude, last.longitude) if last else (trip.origin_lat or DEFAULT_START[0], trip.origin_lng or DEFAULT_START[1])

        self.stdout.write(f"Simulando {len(trips)} veículo(s). Ctrl+C para parar.")
        step = 0
        try:
            while True:
                step += 1
                for trip in trips:
                    lat, lng = positions[trip.pk]
                    lat -= 0.003 + random.uniform(-0.001, 0.001)
                    lng += 0.004 + random.uniform(-0.001, 0.001)
                    positions[trip.pk] = (lat, lng)
                    speed = random.uniform(60, 85)
                    if opts["speeding"] and step % 15 == 0:
                        speed = random.uniform(100, 115)
                    ping = LocationPing.objects.create(
                        vehicle=trip.vehicle, trip=trip, latitude=lat, longitude=lng, speed_kmh=round(speed, 1), heading=135
                    )
                    alert_services.check_speeding(ping)
                    realtime.publish_position(ping)
                time.sleep(opts["interval"])
        except KeyboardInterrupt:
            self.stdout.write("Simulação encerrada.")
