import { Routes, Route, Navigate } from "react-router-dom";
import Landing from "./components/Landing.jsx";
import Login from "./pages/Login.jsx";
import { useAuth } from "./lib/auth.jsx";
import { Loading } from "./components/ui.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Campaigns from "./pages/Campaigns.jsx";
import CampaignDetail from "./pages/CampaignDetail.jsx";
import Compose from "./pages/Compose.jsx";
import Jobs from "./pages/Jobs.jsx";
import JobDetail from "./pages/JobDetail.jsx";
import Intel from "./pages/Intel.jsx";
import Resumes from "./pages/Resumes.jsx";
import Settings from "./pages/Settings.jsx";
import { Workflow, Followups, Replies, NetworkPaths } from "./pages/Planned.jsx";

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/campaigns" element={<Campaigns />} />
      <Route path="/campaigns/:id" element={<CampaignDetail />} />
      <Route path="/compose" element={<Compose />} />
      <Route path="/jobs" element={<Jobs />} />
      <Route path="/jobs/:id" element={<JobDetail />} />
      <Route path="/intel" element={<Intel />} />
      <Route path="/resumes" element={<Resumes />} />
      <Route path="/settings" element={<Settings />} />
      <Route path="/workflows" element={<Workflow />} />
      <Route path="/followups" element={<Followups />} />
      <Route path="/replies" element={<Replies />} />
      <Route path="/network" element={<NetworkPaths />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  const { email, loading } = useAuth();
  return (
    <>
      <Landing />
      {loading ? (
        <div className="fixed inset-0 grid-bg bg-background flex items-center justify-center">
          <Loading label="AUTHENTICATING…" />
        </div>
      ) : email ? (
        <AppRoutes />
      ) : (
        <Login />
      )}
    </>
  );
}
