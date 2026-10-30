import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth.jsx";

const ROLE = { ADMIN: "Administrador", MANAGER: "Gestor", DRIVER: "Motorista" };

export default function Layout() {
  const { user, logout, isManager } = useAuth();
  const links = [
    ["/", "Painel", true],
    ["/vehicles", "Veículos"],
    ["/drivers", "Motoristas"],
    ["/trips", "Viagens"],
    ["/maintenance", "Manutenções"],
    ...(isManager ? [["/map", "Mapa ao vivo"], ["/alerts", "Alertas"], ["/audit", "Auditoria"]] : []),
  ];
  return (
    <div className="shell">
      <aside className="side">
        <div className="brand">FleetTrack</div>
        <nav>
          {links.map(([to, label, end]) => (
            <NavLink key={to} to={to} end={!!end}>
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="me">
          <strong>{user.first_name || user.email}</strong>
          <span>{ROLE[user.role]}</span>
          <button className="link" onClick={logout}>Sair</button>
        </div>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  );
}
