import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth.jsx";
import Layout from "./components/Layout.jsx";
import Activities from "./pages/admin/Activities.jsx";
import ApiKeys from "./pages/admin/ApiKeys.jsx";
import Destinations from "./pages/admin/Destinations.jsx";
import Knowledge from "./pages/admin/Knowledge.jsx";
import Services from "./pages/admin/Services.jsx";
import UsageReport from "./pages/admin/UsageReport.jsx";
import Users from "./pages/admin/Users.jsx";
import Agent from "./pages/Agent.jsx";
import Chat from "./pages/Chat.jsx";
import History from "./pages/History.jsx";
import Login from "./pages/Login.jsx";
import MyUsage from "./pages/MyUsage.jsx";

function Protected({ admin = false, children }) {
  const { user, ready } = useAuth();
  if (!ready) return <p className="center">Cargando…</p>;
  if (!user) return <Navigate to="/login" replace />;
  if (admin && user.role !== "admin") return <Navigate to="/" replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route element={<Protected><Layout /></Protected>}>
        <Route index element={<Navigate to="/chat" replace />} />
        <Route path="chat" element={<Chat />} />
        <Route path="itinerary" element={<Agent key="itinerary" kind="itinerary" />} />
        <Route path="adjust" element={<Agent key="adjust" kind="adjust" />} />
        <Route path="history" element={<History />} />
        <Route path="usage" element={<MyUsage />} />

        <Route path="admin/report" element={<Protected admin><UsageReport /></Protected>} />
        <Route path="admin/users" element={<Protected admin><Users /></Protected>} />
        <Route path="admin/destinations" element={<Protected admin><Destinations /></Protected>} />
        <Route path="admin/activities" element={<Protected admin><Activities /></Protected>} />
        <Route path="admin/services" element={<Protected admin><Services /></Protected>} />
        <Route path="admin/knowledge" element={<Protected admin><Knowledge /></Protected>} />
        <Route path="admin/api-keys" element={<Protected admin><ApiKeys /></Protected>} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}