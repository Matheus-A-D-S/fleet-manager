import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth.jsx";
import Layout from "./components/Layout.jsx";
import { ForgotPassword, Login, Register, ResetPassword, VerifyEmail } from "./pages/AuthPages.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import { Drivers, Maintenance, Trips, Users, Vehicles } from "./pages/Resources.jsx";
import LiveMap from "./pages/LiveMap.jsx";
import Alerts from "./pages/Alerts.jsx";
import Audit from "./pages/Audit.jsx";

function Private({ children, managerOnly, adminOnly }) {
  const { user, loading, isManager, isAdmin } = useAuth();
  if (loading) return <p className="boot">Carregando…</p>;
  if (!user) return <Navigate to="/login" replace />;
  if (managerOnly && !isManager) return <Navigate to="/" replace />;
  if (adminOnly && !isAdmin) return <Navigate to="/" replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/verify-email" element={<VerifyEmail />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/reset-password" element={<ResetPassword />} />
      <Route
        element={
          <Private>
            <Layout />
          </Private>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="vehicles" element={<Vehicles />} />
        <Route path="drivers" element={<Drivers />} />
        <Route path="trips" element={<Trips />} />
        <Route path="maintenance" element={<Maintenance />} />
        <Route path="map" element={<Private managerOnly><LiveMap /></Private>} />
        <Route path="alerts" element={<Private managerOnly><Alerts /></Private>} />
        <Route path="audit" element={<Private managerOnly><Audit /></Private>} />
        <Route path="users" element={<Private adminOnly><Users /></Private>} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
