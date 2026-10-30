import { useCallback, useEffect, useState } from "react";
import api, { errorMessage, unwrap } from "../api.js";
import { TONE, fmtDateTime } from "../constants.js";

export default function Alerts() {
  const [rows, setRows] = useState(null);
  const [filter, setFilter] = useState("open");
  const [err, setErr] = useState("");
  const [info, setInfo] = useState("");

  const load = useCallback(() => {
    const resolved = filter === "open" ? false : filter === "resolved" ? true : undefined;
    api
      .get("/alerts/", { params: { page_size: 100, resolved } })
      .then((r) => setRows(unwrap(r)))
      .catch((e) => setErr(errorMessage(e)));
  }, [filter]);
  useEffect(load, [load]);

  const resolve = async (a) => {
    await api.post(`/alerts/${a.id}/resolve/`).catch((e) => setErr(errorMessage(e)));
    load();
  };
  const scan = async () => {
    try {
      const { data } = await api.post("/alerts/scan/");
      setInfo(data.detail + " Atualize a lista em alguns segundos.");
    } catch (e) {
      setErr(errorMessage(e));
    }
  };

  return (
    <>
      <header className="page-head">
        <h1>Alertas</h1>
        <div className="tools">
          <select value={filter} onChange={(e) => setFilter(e.target.value)}>
            <option value="open">Abertos</option>
            <option value="resolved">Resolvidos</option>
            <option value="all">Todos</option>
          </select>
          <button className="primary" onClick={scan}>Verificar agora</button>
        </div>
      </header>
      {err && <p className="msg bad">{err}</p>}
      {info && <p className="msg ok">{info}</p>}
      {!rows ? (
        <p className="boot">Carregando…</p>
      ) : rows.length === 0 ? (
        <p className="empty">Nenhum alerta {filter === "open" ? "aberto" : "encontrado"}.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>Gravidade</th><th>Alerta</th><th>Quando</th><th>E-mail</th><th /></tr>
            </thead>
            <tbody>
              {rows.map((a) => (
                <tr key={a.id} className={`row tone-${TONE[a.severity]}`}>
                  <td>{a.severity_display}</td>
                  <td><b>{a.title}</b><br /><span className="muted">{a.message}</span></td>
                  <td>{fmtDateTime(a.created_at)}</td>
                  <td>{a.email_sent_at ? `Enviado ${fmtDateTime(a.email_sent_at)}` : "Pendente"}</td>
                  <td className="actions">
                    {!a.resolved && <button className="link" onClick={() => resolve(a)}>Marcar como resolvido</button>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
