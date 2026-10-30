import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import api, { errorMessage } from "../api.js";
import { useAuth } from "../auth.jsx";

function Shell({ title, children }) {
  return (
    <div className="auth">
      <div className="auth-panel">
        <div className="brand">FleetTrack</div>
        <h1>{title}</h1>
        {children}
      </div>
    </div>
  );
}

const Msg = ({ ok, children }) => (children ? <p className={ok ? "msg ok" : "msg bad"}>{children}</p> : null);

export function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [f, setF] = useState({ email: "", password: "" });
  const [err, setErr] = useState("");
  const [unverified, setUnverified] = useState(false);
  const [info, setInfo] = useState("");
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    setInfo("");
    setUnverified(false);
    try {
      await login(f.email, f.password);
      nav("/");
    } catch (ex) {
      setUnverified(ex.response?.status === 403);
      setErr(ex.response?.status === 401 ? "E-mail ou senha incorretos." : errorMessage(ex));
    }
  };
  const resend = async () => {
    await api.post("/auth/resend-verification/", { email: f.email });
    setInfo("Se a conta existir, enviamos um novo e-mail de confirmação.");
  };

  return (
    <Shell title="Entrar">
      <form onSubmit={submit}>
        <label>E-mail<input type="email" value={f.email} onChange={set("email")} required autoFocus /></label>
        <label>Senha<input type="password" value={f.password} onChange={set("password")} required /></label>
        <Msg>{err}</Msg>
        <Msg ok>{info}</Msg>
        {unverified && <button type="button" className="link" onClick={resend}>Reenviar e-mail de confirmação</button>}
        <button className="primary">Entrar</button>
      </form>
      <p className="alt"><Link to="/forgot-password">Esqueci minha senha</Link> · <Link to="/register">Criar conta</Link></p>
    </Shell>
  );
}

export function Register() {
  const [f, setF] = useState({ first_name: "", last_name: "", email: "", password: "" });
  const [err, setErr] = useState("");
  const [done, setDone] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    try {
      await api.post("/auth/register/", f);
      setDone(true);
    } catch (ex) {
      setErr(errorMessage(ex));
    }
  };

  if (done)
    return (
      <Shell title="Confirme seu e-mail">
        <p>Enviamos um link de confirmação para <strong>{f.email}</strong>. Abra o e-mail e clique no link para ativar a conta.</p>
        <p className="alt"><Link to="/login">Ir para o login</Link></p>
      </Shell>
    );
  return (
    <Shell title="Criar conta">
      <form onSubmit={submit}>
        <label>Nome<input value={f.first_name} onChange={set("first_name")} required /></label>
        <label>Sobrenome<input value={f.last_name} onChange={set("last_name")} /></label>
        <label>E-mail<input type="email" value={f.email} onChange={set("email")} required /></label>
        <label>Senha<input type="password" value={f.password} onChange={set("password")} required minLength={8} /></label>
        <Msg>{err}</Msg>
        <button className="primary">Criar conta</button>
      </form>
      <p className="alt">Já tem conta? <Link to="/login">Entrar</Link></p>
    </Shell>
  );
}

export function VerifyEmail() {
  const [params] = useSearchParams();
  const [state, setState] = useState({ status: "loading", text: "" });
  useEffect(() => {
    const token = params.get("token");
    if (!token) return setState({ status: "bad", text: "Link incompleto." });
    api
      .post("/auth/verify-email/", { token })
      .then((r) => setState({ status: "ok", text: r.data.detail }))
      .catch((ex) => setState({ status: "bad", text: errorMessage(ex) }));
  }, [params]);
  return (
    <Shell title="Confirmação de e-mail">
      {state.status === "loading" ? <p>Verificando…</p> : <Msg ok={state.status === "ok"}>{state.text}</Msg>}
      <p className="alt"><Link to="/login">Ir para o login</Link></p>
    </Shell>
  );
}

export function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [info, setInfo] = useState("");
  const [err, setErr] = useState("");
  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    try {
      const { data } = await api.post("/auth/password-reset/", { email });
      setInfo(data.detail);
    } catch (ex) {
      setErr(errorMessage(ex));
    }
  };
  return (
    <Shell title="Redefinir senha">
      <form onSubmit={submit}>
        <label>E-mail da conta<input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus /></label>
        <Msg>{err}</Msg>
        <Msg ok>{info}</Msg>
        <button className="primary">Enviar link</button>
      </form>
      <p className="alt"><Link to="/login">Voltar ao login</Link></p>
    </Shell>
  );
}

export function ResetPassword() {
  const [params] = useSearchParams();
  const nav = useNavigate();
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [done, setDone] = useState(false);
  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    try {
      await api.post("/auth/password-reset/confirm/", { uid: params.get("uid"), token: params.get("token"), password });
      setDone(true);
      setTimeout(() => nav("/login"), 1500);
    } catch (ex) {
      setErr(errorMessage(ex));
    }
  };
  return (
    <Shell title="Nova senha">
      {done ? (
        <Msg ok>Senha alterada. Redirecionando para o login…</Msg>
      ) : (
        <form onSubmit={submit}>
          <label>Nova senha<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} autoFocus /></label>
          <Msg>{err}</Msg>
          <button className="primary">Salvar senha</button>
        </form>
      )}
    </Shell>
  );
}
