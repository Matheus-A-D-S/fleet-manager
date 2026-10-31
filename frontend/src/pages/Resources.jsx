import ResourcePage from "./ResourcePage.jsx";
import { useAuth } from "../auth.jsx";
import { LICENSE_CATEGORIES, TONE, TRIP_STATUS, VEHICLE_STATUS, VEHICLE_TYPES, brl, fmtDate, fmtDateTime, isPast } from "../constants.js";

const vehicleFields = [
  { name: "plate", label: "Placa", required: true },
  { name: "brand", label: "Marca", required: true },
  { name: "model", label: "Modelo", required: true },
  { name: "year", label: "Ano", type: "number", required: true },
  { name: "vehicle_type", label: "Tipo", type: "select", choices: VEHICLE_TYPES },
  { name: "status", label: "Situação", type: "select", choices: VEHICLE_STATUS },
  { name: "odometer_km", label: "Odômetro (km)", type: "number" },
  { name: "capacity_kg", label: "Capacidade (kg)", type: "number" },
  { name: "next_maintenance_km", label: "Próxima revisão (km)", type: "number" },
  { name: "next_maintenance_date", label: "Próxima revisão (data)", type: "date" },
  { name: "insurance_expiry", label: "Vencimento do seguro", type: "date" },
  { name: "licensing_expiry", label: "Vencimento do licenciamento", type: "date" },
];

export const Vehicles = () => (
  <ResourcePage
    title="Veículos"
    noun="veículo"
    endpoint="/fleet/vehicles/"
    fields={vehicleFields}
    tone={(r) => TONE[r.status]}
    columns={[
      { label: "Placa", key: "plate" },
      { label: "Veículo", render: (r) => `${r.brand} ${r.model} (${r.year})` },
      { label: "Tipo", key: "vehicle_type_display" },
      { label: "Odômetro", render: (r) => `${r.odometer_km.toLocaleString("pt-BR")} km` },
      { label: "Seguro até", render: (r) => fmtDate(r.insurance_expiry) },
      { label: "Situação", key: "status_display" },
    ]}
  />
);

const driverFields = [
  { name: "full_name", label: "Nome completo", required: true, wide: true },
  { name: "license_number", label: "CNH", required: true },
  { name: "license_category", label: "Categoria", type: "select", choices: LICENSE_CATEGORIES },
  { name: "license_expiry", label: "Validade da CNH", type: "date", required: true },
  { name: "phone", label: "Telefone" },
  {
    name: "user",
    label: "Usuário de acesso",
    type: "select",
    optionsFrom: { endpoint: "/auth/users/", params: { role: "DRIVER" }, label: (u) => u.email },
  },
  { name: "is_active", label: "Ativo", type: "checkbox", default: true },
];

export const Drivers = () => (
  <ResourcePage
    title="Motoristas"
    noun="motorista"
    endpoint="/fleet/drivers/"
    fields={driverFields}
    tone={(r) => (!r.is_active ? "idle" : isPast(r.license_expiry) ? "bad" : "ok")}
    columns={[
      { label: "Nome", key: "full_name" },
      { label: "CNH", render: (r) => `${r.license_number} (${r.license_category})` },
      { label: "Validade", render: (r) => fmtDate(r.license_expiry) },
      { label: "Telefone", key: "phone" },
      { label: "Acesso", render: (r) => r.user_email || "—" },
      { label: "Ativo", render: (r) => (r.is_active ? "Sim" : "Não") },
    ]}
  />
);

const tripFields = [
  { name: "vehicle", label: "Veículo", type: "select", required: true, optionsFrom: { endpoint: "/fleet/vehicles/", label: (v) => `${v.plate} - ${v.model}` } },
  { name: "driver", label: "Motorista", type: "select", required: true, optionsFrom: { endpoint: "/fleet/drivers/", params: { is_active: true }, label: (d) => d.full_name } },
  { name: "origin", label: "Origem", required: true },
  { name: "destination", label: "Destino", required: true },
  { name: "scheduled_start", label: "Saída prevista", type: "datetime-local", required: true },
  { name: "scheduled_arrival", label: "Chegada prevista", type: "datetime-local", required: true },
  { name: "cargo_description", label: "Carga", type: "textarea", wide: true },
  { name: "cargo_weight_kg", label: "Peso (kg)", type: "number" },
  { name: "notes", label: "Observações", type: "textarea", wide: true },
];

export const Trips = () => (
  <ResourcePage
    title="Viagens"
    noun="viagem"
    createLabel="Nova viagem"
    endpoint="/logistics/trips/"
    fields={tripFields}
    tone={(r) => TONE[r.status]}
    rowActions={[
      { label: "Iniciar", path: "start", when: (r) => r.status === "PLANNED" },
      { label: "Concluir", path: "complete", when: (r) => r.status === "IN_PROGRESS" },
      { label: "Cancelar", path: "cancel", managerOnly: true, when: (r) => ["PLANNED", "IN_PROGRESS"].includes(r.status) },
    ]}
    columns={[
      { label: "Código", key: "code" },
      { label: "Veículo", key: "vehicle_plate" },
      { label: "Motorista", key: "driver_name" },
      { label: "Rota", render: (r) => `${r.origin} → ${r.destination}` },
      { label: "Chegada prevista", render: (r) => fmtDateTime(r.scheduled_arrival) },
      { label: "Situação", key: "status_display" },
    ]}
  />
);

const maintFields = [
  { name: "vehicle", label: "Veículo", type: "select", required: true, optionsFrom: { endpoint: "/fleet/vehicles/", label: (v) => `${v.plate} - ${v.model}` } },
  { name: "kind", label: "Tipo", type: "select", choices: [["PREVENTIVE", "Preventiva"], ["CORRECTIVE", "Corretiva"]] },
  { name: "performed_at", label: "Data", type: "date", required: true },
  { name: "odometer_km", label: "Odômetro (km)", type: "number", required: true },
  { name: "cost", label: "Custo (R$)", type: "number" },
  { name: "description", label: "Descrição", type: "textarea", required: true, wide: true },
];

export const Maintenance = () => (
  <ResourcePage
    title="Manutenções"
    noun="manutenção"
    createLabel="Registrar manutenção"
    endpoint="/fleet/maintenance/"
    fields={maintFields}
    searchable={false}
    columns={[
      { label: "Veículo", key: "vehicle_plate" },
      { label: "Tipo", key: "kind_display" },
      { label: "Data", render: (r) => fmtDate(r.performed_at) },
      { label: "Odômetro", render: (r) => `${r.odometer_km.toLocaleString("pt-BR")} km` },
      { label: "Custo", render: (r) => brl(r.cost) },
      { label: "Descrição", key: "description" },
    ]}
  />
);

const ROLES = [["ADMIN", "Administrador"], ["MANAGER", "Gestor"], ["DRIVER", "Motorista"]];

const userFields = [
  { name: "email", label: "E-mail", type: "email", required: true, createOnly: true, wide: true },
  { name: "first_name", label: "Nome", required: true },
  { name: "last_name", label: "Sobrenome" },
  { name: "role", label: "Perfil", type: "select", choices: ROLES },
  { name: "is_active", label: "Ativo", type: "checkbox", default: true },
];

export const Users = () => {
  const { user } = useAuth();
  return (
    <ResourcePage
      title="Equipe"
      noun="usuário"
      createLabel="Convidar usuário"
      endpoint="/auth/users/"
      fields={userFields}
      canWrite={user.role === "ADMIN"}
      allowDelete={false}
      tone={(r) => (!r.is_active ? "idle" : r.is_email_verified ? "ok" : "warn")}
      rowActions={[{ label: "Reenviar convite", path: "resend-invite", managerOnly: true, when: (r) => r.is_active && !r.is_email_verified }]}
      columns={[
        { label: "Nome", render: (r) => [r.first_name, r.last_name].filter(Boolean).join(" ") || "—" },
        { label: "E-mail", key: "email" },
        { label: "Perfil", key: "role_display" },
        { label: "Situação", render: (r) => (!r.is_active ? "Desativado" : r.is_email_verified ? "Ativo" : "Convite pendente") },
      ]}
    />
  );
};
