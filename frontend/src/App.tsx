// frontend/src/App.tsx
// Urban Intelligence Framework - Main Application Component

import { Routes, Route, Navigate } from "react-router-dom";
import { Layout } from "@/components/Layout";
import {
  Dashboard,
  Predict,
  Cities,
  Analytics,
  Experiments,
  Monitoring,
  Settings,
} from "@/pages";

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/predict" element={<Predict />} />
        <Route path="/cities" element={<Cities />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/experiments" element={<Experiments />} />
        <Route path="/monitoring" element={<Monitoring />} />
        <Route path="/settings" element={<Settings />} />
        {/* Redirect unknown routes to dashboard */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  );
}

export default App;
