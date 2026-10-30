import { useEffect, useState } from "react";
import api, { errorMessage, unwrap } from "../api.js";
import { fmtDateTime } from "../constants.js";

const MODEL = {
  "fleet.Vehicle": "Veículo",
  "fleet.Driver": "Motorista",
  "fleet.MaintenanceRecord": "Manutenção",
  "logistics.Trip": "Viagem",
};

const show = (v) => (v === null || v === "" || v === undefined ? "vazio" : typeof v === "object" ? JSON.stringify(v) : String(v));

function Changes({ log }) {
  if (log.action === "CREATE") return <span className="muted">Registro criado</span>;
  if (log.action === "DELETE") return <span className="muted">Registro excluído</span>;
  const entries = Object.entries(log.changes || {}).filter(([, v]) => v && typeof v === "object" && "from" in v);
  return (
    <>
      {log.action === "ACTION" && <b>{log.changes.action}</b>}
      {entries.map(([field, v]) => (
        <div key={field} className="muted">{field}: {show(v.from)} → {show(v.to)}</div>
      ))}
    </>
  );
}

export default function Audit() {
  const [rows, setRows] = useState(null);
  const [model, setModel] = useState("");
  const [err, setErr] = useState("");

  useEffect(() => {
    api
      .get("/audit/", { params: { page_size: 100, model: model || undefined } })
      .then((r) => setRows(unwrap(r)))
      .catch((e) => setErr(errorMessage(e)));
  }, [model]);

  return (
    <>
      <header className="page-head">
        <h1>Auditoria</h1>
        <div className="tools">
          <select value={model} onChange={(e) => setModel(e.target.value)}>
            <option value="">Todos os registros</option>
            {Object.entries(MODEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </div>
      </header>
      {err && <p className="msg bad">{err}</p>}
      {!rows ? (
        <p className="boot">Carregando…</p>
      ) : rows.length === 0 ? (
        <p className="empty">Nenhuma alteração registrada ainda.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>Quando</th><th>Quem</th><th>O quê</th><th>Detalhes</th><th>IP</th></tr>
            </thead>
            <tbody>
              {rows.map((l) => (
                <tr key={l.id}>
                  <td>{fmtDateTime(l.created_at)}</td>
                  <td>{l.user_email || "—"}</td>
                  <td>{l.action_display} · {MODEL[l.model] || l.model}<br /><span className="muted">{l.object_repr}</span></td>
                  <td><Changes log={l} /></td>
                  <td>{l.ip_address || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
