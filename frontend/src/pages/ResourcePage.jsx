import { useCallback, useEffect, useState } from "react";
import api, { errorMessage, unwrap } from "../api.js";
import { useAuth } from "../auth.jsx";

const pad = (n) => String(n).padStart(2, "0");
const toLocalInput = (iso) => {
  if (!iso) return "";
  const d = new Date(iso);
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
};

const initialValues = (fields, row) =>
  Object.fromEntries(
    fields.map((f) => {
      const raw = row ? row[f.name] : f.default;
      if (f.type === "checkbox") return [f.name, raw ?? true];
      if (f.type === "datetime-local") return [f.name, toLocalInput(raw)];
      if (f.type === "select" && !row && f.choices && raw == null) return [f.name, f.choices[0][0]];
      return [f.name, raw ?? ""];
    })
  );

function toPayload(fields, values) {
  const out = {};
  for (const f of fields) {
    let v = values[f.name];
    if (f.type === "checkbox") v = !!v;
    else if (v === "") v = f.type === "text" || f.type === "textarea" || f.choices ? "" : null;
    else if (f.type === "number" || (f.type === "select" && f.optionsFrom)) v = Number(v);
    out[f.name] = v;
  }
  return out;
}

export default function ResourcePage({ title, noun, endpoint, columns, fields, rowActions = [], tone, searchable = true, createLabel }) {
  const { isManager } = useAuth();
  const [rows, setRows] = useState(null);
  const [q, setQ] = useState("");
  const [err, setErr] = useState("");
  const [opts, setOpts] = useState({});
  const [editing, setEditing] = useState(null); // null | { row?: obj }
  const [values, setValues] = useState({});
  const [formErr, setFormErr] = useState("");

  const load = useCallback(() => {
    api
      .get(endpoint, { params: { page_size: 100, search: q || undefined } })
      .then((r) => {
        setRows(unwrap(r));
        setErr("");
      })
      .catch((e) => setErr(errorMessage(e)));
  }, [endpoint, q]);

  useEffect(() => {
    const t = setTimeout(load, q ? 300 : 0);
    return () => clearTimeout(t);
  }, [load, q]);

  useEffect(() => {
    if (!isManager) return;
    fields
      .filter((f) => f.optionsFrom)
      .forEach((f) =>
        api
          .get(f.optionsFrom.endpoint, { params: { page_size: 200, ...f.optionsFrom.params } })
          .then((r) => setOpts((o) => ({ ...o, [f.name]: unwrap(r) })))
          .catch(() => {})
      );
  }, [isManager, fields]);

  const openForm = (row) => {
    setValues(initialValues(fields, row));
    setFormErr("");
    setEditing({ row });
  };

  const save = async (e) => {
    e.preventDefault();
    const payload = toPayload(fields, values);
    try {
      if (editing.row) await api.patch(`${endpoint}${editing.row.id}/`, payload);
      else await api.post(endpoint, payload);
      setEditing(null);
      load();
    } catch (ex) {
      setFormErr(errorMessage(ex));
    }
  };

  const remove = async (row) => {
    if (!window.confirm(`Excluir ${noun}? Esta ação não pode ser desfeita.`)) return;
    try {
      await api.delete(`${endpoint}${row.id}/`);
      load();
    } catch (ex) {
      setErr(errorMessage(ex));
    }
  };

  const runAction = async (row, a) => {
    try {
      await api.post(`${endpoint}${row.id}/${a.path}/`);
      load();
    } catch (ex) {
      setErr(errorMessage(ex));
    }
  };

  return (
    <>
      <header className="page-head">
        <h1>{title}</h1>
        <div className="tools">
          {searchable && <input type="search" placeholder="Buscar" value={q} onChange={(e) => setQ(e.target.value)} />}
          {isManager && <button className="primary" onClick={() => openForm(null)}>{createLabel || `Novo ${noun}`}</button>}
        </div>
      </header>
      {err && <p className="msg bad">{err}</p>}
      {!rows ? (
        <p className="boot">Carregando…</p>
      ) : rows.length === 0 ? (
        <p className="empty">Nenhum registro ainda.{isManager ? ` Use “${createLabel || `Novo ${noun}`}” para começar.` : ""}</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                {columns.map((c) => <th key={c.label}>{c.label}</th>)}
                <th />
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id} className={tone ? `row tone-${tone(row)}` : "row"}>
                  {columns.map((c) => <td key={c.label}>{c.render ? c.render(row) : row[c.key] ?? "—"}</td>)}
                  <td className="actions">
                    {rowActions.filter((a) => a.when(row) && (!a.managerOnly || isManager)).map((a) => (
                      <button key={a.path} className="link" onClick={() => runAction(row, a)}>{a.label}</button>
                    ))}
                    {isManager && <button className="link" onClick={() => openForm(row)}>Editar</button>}
                    {isManager && <button className="link danger" onClick={() => remove(row)}>Excluir</button>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {editing && (
        <div className="overlay" onClick={() => setEditing(null)}>
          <form className="modal" onClick={(e) => e.stopPropagation()} onSubmit={save}>
            <h2>{editing.row ? `Editar ${noun}` : `Novo ${noun}`}</h2>
            <div className="fields">
              {fields.map((f) => (
                <label key={f.name} className={f.wide ? "wide" : ""}>
                  {f.label}
                  {f.type === "textarea" ? (
                    <textarea rows={3} value={values[f.name]} onChange={(e) => setValues({ ...values, [f.name]: e.target.value })} />
                  ) : f.type === "checkbox" ? (
                    <input type="checkbox" checked={!!values[f.name]} onChange={(e) => setValues({ ...values, [f.name]: e.target.checked })} />
                  ) : f.type === "select" ? (
                    <select
                      value={values[f.name]}
                      required={f.required}
                      onChange={(e) => setValues({ ...values, [f.name]: e.target.value })}
                    >
                      {f.optionsFrom ? (
                        <>
                          <option value="">{f.required ? "Selecione…" : "Nenhum"}</option>
                          {(opts[f.name] || []).map((o) => <option key={o.id} value={o.id}>{f.optionsFrom.label(o)}</option>)}
                        </>
                      ) : (
                        f.choices.map(([v, l]) => <option key={v} value={v}>{l}</option>)
                      )}
                    </select>
                  ) : (
                    <input
                      type={f.type || "text"}
                      step={f.type === "number" ? "any" : undefined}
                      required={f.required}
                      value={values[f.name]}
                      onChange={(e) => setValues({ ...values, [f.name]: e.target.value })}
                    />
                  )}
                </label>
              ))}
            </div>
            {formErr && <p className="msg bad">{formErr}</p>}
            <div className="modal-actions">
              <button type="button" className="link" onClick={() => setEditing(null)}>Cancelar</button>
              <button className="primary">Salvar</button>
            </div>
          </form>
        </div>
      )}
    </>
  );
}
