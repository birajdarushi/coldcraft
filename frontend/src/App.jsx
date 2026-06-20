import { Routes, Route, Navigate } from "react-router-dom";
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

export default function App() {
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
