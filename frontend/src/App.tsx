// frontend/src/App.tsx
// Urban Intelligence Framework v2.0.0
// Root application component with routing

import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Layout from "@/components/Layout";
import DashboardPage from "@/pages/DashboardPage";
import PredictPage from "@/pages/PredictPage";
import CitiesPage from "@/pages/CitiesPage";
import AnalyticsPage from "@/pages/AnalyticsPage";
import ExperimentsPage from "@/pages/ExperimentsPage";
import MonitoringPage from "@/pages/MonitoringPage";
import SettingsPage from "@/pages/SettingsPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/predict" element={<PredictPage />} />
          <Route path="/cities" element={<CitiesPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/experiments" element={<ExperimentsPage />} />
          <Route path="/monitoring" element={<MonitoringPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
