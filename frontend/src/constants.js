export const VEHICLE_STATUS = [
  ["AVAILABLE", "Disponível"],
  ["IN_USE", "Em viagem"],
  ["MAINTENANCE", "Em manutenção"],
  ["INACTIVE", "Inativo"],
];
export const VEHICLE_TYPES = [
  ["TRUCK", "Caminhão"],
  ["VAN", "Van"],
  ["CAR", "Carro"],
  ["MOTORCYCLE", "Moto"],
];
export const TRIP_STATUS = [
  ["PLANNED", "Planejada"],
  ["IN_PROGRESS", "Em andamento"],
  ["COMPLETED", "Concluída"],
  ["CANCELLED", "Cancelada"],
];
export const LICENSE_CATEGORIES = ["A", "B", "C", "D", "E"].map((c) => [c, c]);

// Cor semântica de cada estado (ver classes .tone-* no CSS)
export const TONE = {
  AVAILABLE: "ok",
  IN_USE: "road",
  MAINTENANCE: "warn",
  INACTIVE: "idle",
  PLANNED: "idle",
  IN_PROGRESS: "road",
  COMPLETED: "ok",
  CANCELLED: "idle",
  INFO: "idle",
  WARNING: "warn",
  CRITICAL: "bad",
};

export const fmtDate = (d) => (d ? d.split("-").reverse().join("/") : "—");
export const fmtDateTime = (iso) =>
  iso ? new Date(iso).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" }) : "—";
export const brl = (v) => Number(v ?? 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
export const isPast = (isoDate) => !!isoDate && isoDate < new Date().toISOString().slice(0, 10);
