import { Routes, Route, Navigate } from "react-router-dom";
import { InboxProvider } from "./lib/InboxContext.jsx";
import Landing from "./components/Landing.jsx";
import Cursor from "./components/Cursor.jsx";
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
import Inbox from "./pages/Inbox.jsx";
import Pipeline from "./pages/Pipeline.jsx";
import Apply from "./pages/Apply.jsx";
import Network from "./pages/Network.jsx";
import Roadmap from "./pages/Roadmap.jsx";
import Memory from "./pages/Memory.jsx";

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/inbox" element={<Inbox />} />
      <Route path="/pipeline" element={<Pipeline />} />
      <Route path="/apply" element={<Apply />} />
      <Route path="/network" element={<Network />} />
      <Route path="/roadmap" element={<Roadmap />} />
      <Route path="/memory" element={<Memory />} />
      <Route path="/settings" element={<Settings />} />
      <Route path="/campaigns" element={<Campaigns />} />
      <Route path="/campaigns/:id" element={<CampaignDetail />} />
      <Route path="/jobs" element={<Jobs />} />
      <Route path="/jobs/:id" element={<JobDetail />} />
      <Route path="/intel" element={<Intel />} />
      <Route path="/resumes" element={<Resumes />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  const { email, loading } = useAuth();
  return (
    <>
      <Cursor />
      <Landing />
      {loading ? (
        <div className="fixed inset-0 grid-bg bg-background flex items-center justify-center">
          <Loading label="AUTHENTICATING…" />
        </div>
      ) : email ? (
        <InboxProvider>
          <AppRoutes />
        </InboxProvider>
        ) : (
        <Login />
      )}
    </>
  );
}
