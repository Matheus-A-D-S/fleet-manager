import { useEffect, useRef, useState } from "react";
import { CircleMarker, MapContainer, Polyline, TileLayer, Tooltip, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import api, { errorMessage, getTokens } from "../api.js";
import { fmtDateTime } from "../constants.js";

const STALE_MS = 10 * 60 * 1000;
const isStale = (p) => Date.now() - new Date(p.recorded_at).getTime() > STALE_MS;

const upsert = (list, p) => {
  const i = list.findIndex((x) => x.vehicle_id === p.vehicle_id);
  if (i === -1) return [...list, p];
  const next = [...list];
  next[i] = p;
  return next;
};

const STATUS_TEXT = { live: "Ao vivo", connecting: "Conectando…", reconnecting: "Reconectando…" };

function FitOnce({ points }) {
  const map = useMap();
  const done = useRef(false);
  useEffect(() => {
    if (points.length && !done.current) {
      map.fitBounds(points, { padding: [48, 48], maxZoom: 12 });
      done.current = true;
    }
  }, [points, map]);
  return null;
}

export default function LiveMap() {
  const [live, setLive] = useState(null);
  const [err, setErr] = useState("");
  const [sel, setSel] = useState(null);
  const [track, setTrack] = useState([]);
  const [wsState, setWsState] = useState("connecting");

  // Carga inicial e, se o WebSocket cair, atualização por polling a cada 10 s.
  useEffect(() => {
    let stop = false;
    const load = () =>
      api
        .get("/logistics/live/")
        .then((r) => {
          if (!stop) {
            setLive(r.data);
            setErr("");
          }
        })
        .catch((e) => !stop && setErr(errorMessage(e)));
    load();
    if (wsState === "live") return () => (stop = true);
    const id = setInterval(load, 10000);
    return () => {
      stop = true;
      clearInterval(id);
    };
  }, [wsState]);

  // WebSocket com reconexão exponencial; o token é renovado antes de cada tentativa.
  useEffect(() => {
    let ws;
    let timer;
    let stopped = false;
    let attempt = 0;

    const connect = async () => {
      try {
        await api.get("/auth/me/"); // força a renovação do access token, se preciso
      } catch {
        return;
      }
      if (stopped) return;
      const proto = window.location.protocol === "https:" ? "wss" : "ws";
      ws = new WebSocket(`${proto}://${window.location.host}/ws/fleet/?token=${getTokens().access}`);
      ws.onopen = () => {
        attempt = 0;
        setWsState("live");
      };
      ws.onmessage = (e) => setLive((cur) => upsert(cur || [], JSON.parse(e.data)));
      ws.onclose = () => {
        if (stopped) return;
        setWsState("reconnecting");
        timer = setTimeout(connect, Math.min(1000 * 2 ** attempt++, 15000));
      };
    };

    connect();
    return () => {
      stopped = true;
      clearTimeout(timer);
      ws?.close();
    };
  }, []);

  const selected = (live || []).find((x) => x.vehicle_id === sel);

  // Trajeto da viagem do veículo selecionado; novos pontos chegam pelo WebSocket.
  useEffect(() => {
    if (!selected?.trip_id) return setTrack([]);
    api
      .get(`/logistics/trips/${selected.trip_id}/track/`)
      .then((r) => setTrack(r.data.map((p) => [p.latitude, p.longitude])))
      .catch(() => setTrack([]));
  }, [sel, selected?.trip_id]);

  useEffect(() => {
    if (!selected) return;
    setTrack((t) => {
      const last = t[t.length - 1];
      return last && last[0] === selected.latitude && last[1] === selected.longitude
        ? t
        : [...t, [selected.latitude, selected.longitude]];
    });
  }, [selected?.latitude, selected?.longitude]);

  const points = (live || []).map((p) => [p.latitude, p.longitude]);

  return (
    <>
      <header className="page-head">
        <h1>Mapa ao vivo</h1>
        <span className={`conn tone-${wsState === "live" ? "ok" : "warn"}`}>
          <span className="dot" /> {STATUS_TEXT[wsState]}
        </span>
      </header>
      {err && <p className="msg bad">{err}</p>}
      <div className="map-layout">
        <ul className="fleet-list">
          {live?.length === 0 && <li className="empty">Nenhum veículo enviou posição nas últimas 24 horas.</li>}
          {(live || []).map((p) => (
            <li key={p.vehicle_id}>
              <button className={p.vehicle_id === sel ? "on" : ""} onClick={() => setSel(p.vehicle_id)}>
                <b>{p.plate}</b>
                <span>{isStale(p) ? "Sem sinal" : `${Math.round(p.speed_kmh)} km/h`}</span>
                <small>{p.trip_code || "Sem viagem"} · {fmtDateTime(p.recorded_at)}</small>
              </button>
            </li>
          ))}
        </ul>
        <MapContainer className="map" center={[-14.2, -51.9]} zoom={4} scrollWheelZoom>
          <TileLayer attribution="&copy; OpenStreetMap" url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" />
          <FitOnce points={points} />
          {track.length > 1 && <Polyline positions={track} pathOptions={{ color: "#1f6f8b", weight: 3, dashArray: "6 6" }} />}
          {(live || []).map((p) => (
            <CircleMarker
              key={p.vehicle_id}
              center={[p.latitude, p.longitude]}
              radius={p.vehicle_id === sel ? 11 : 8}
              pathOptions={{ color: "#14303a", weight: 2, fillColor: isStale(p) ? "#9aa39e" : "#f2a900", fillOpacity: 1 }}
              eventHandlers={{ click: () => setSel(p.vehicle_id) }}
            >
              <Tooltip>{p.plate} · {Math.round(p.speed_kmh)} km/h</Tooltip>
            </CircleMarker>
          ))}
        </MapContainer>
      </div>
    </>
  );
}
