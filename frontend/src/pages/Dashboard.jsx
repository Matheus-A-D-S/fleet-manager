import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import api, { errorMessage } from "../api.js";
import { useAuth } from "../auth.jsx";
import { TONE, TRIP_STATUS, VEHICLE_STATUS } from "../constants.js";

function Breakdown({ title, rows, counts }) {
  const total = rows.reduce((s, [k]) => s + (counts[k] || 0), 0);
  return (
    <section className="block">
      <h2>{title} <span className="count">{total}</span></h2>
      <div className="bar" role="img" aria-label={`${title}: ${total}`}>
        {rows.map(([k]) =>
          counts[k] ? <i key={k} className={`tone-${TONE[k]}`} style={{ flexGrow: counts[k] }} /> : null
        )}
      </div>
      <ul className="legend">
        {rows.map(([k, label]) => (
          <li key={k}>
            <span className={`dot tone-${TONE[k]}`} />
            {label}
            <b>{counts[k] || 0}</b>
          </li>
        ))}
      </ul>
    </section>
  );
}

export default function Dashboard() {
  const { isManager } = useAuth();
  const [d, setD] = useState(null);
  const [err, setErr] = useState("");
  useEffect(() => {
    api.get("/logistics/dashboard/").then((r) => setD(r.data)).catch((e) => setErr(errorMessage(e)));
  }, []);

  if (err) return <p className="msg bad">{err}</p>;
  if (!d) return <p className="boot">Carregando…</p>;
  return (
    <>
      <header className="page-head"><h1>Painel</h1></header>
      {isManager && d.open_alerts > 0 && (
        <Link to="/alerts" className={`notice ${d.critical_alerts ? "tone-bad" : "tone-warn"}`}>
          {d.open_alerts} alerta(s) aberto(s){d.critical_alerts ? `, ${d.critical_alerts} crítico(s)` : ""}. Ver alertas
        </Link>
      )}
      <div className="grid2">
        <Breakdown title="Veículos" rows={VEHICLE_STATUS} counts={d.vehicles} />
        <Breakdown title="Viagens" rows={TRIP_STATUS} counts={d.trips} />
      </div>
      <p className="muted">{d.drivers_active} motorista(s) ativo(s).</p>
    </>
  );
}
