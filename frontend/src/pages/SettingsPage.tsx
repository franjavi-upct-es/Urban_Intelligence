// frontend/src/pages/SettingsPage.tsx
// Urban Intelligence Framework v2.0.0
// Settings page — API connection, model parameters, display preferences

import { useState } from "react";
import { Save, RotateCcw, ExternalLink } from "lucide-react";
import { SectionHeader } from "@/components/ui";

interface AppSettings {
  apiUrl: string;
  wsUrl: string;
  defaultCity: string;
  autoRefreshInterval: number;
  showConfidenceInterval: boolean;
  nOptunTrials: number;
  transferLearningEnabled: boolean;
  nlpEnabled: boolean;
}

const DEFAULTS: AppSettings = {
  apiUrl: import.meta.env.VITE_API_URL ?? "http://localhost:8000",
  wsUrl: import.meta.env.VITE_WS_URL ?? "ws://localhost:8000",
  defaultCity: "london",
  autoRefreshInterval: 10,
  showConfidenceInterval: true,
  nOptunTrials: 50,
  transferLearningEnabled: true,
  nlpEnabled: false,
};

function SectionCard({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="card p-6 space-y-4">
      <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">
        {title}
      </h3>
      {children}
    </div>
  );
}

function Toggle({
  label,
  description,
  checked,
  onChange,
}: {
  label: string;
  description?: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="flex items-start justify-between gap-4 cursor-pointer">
      <div>
        <p className="text-sm font-medium text-slate-300">{label}</p>
        {description && (
          <p className="text-xs text-slate-600 mt-0.5">{description}</p>
        )}
      </div>
      <button
        type="button"
        onClick={() => onChange(!checked)}
        className={`relative w-11 h-6 rounded-full transition-colors duration-200 shrink-0 ${checked ? "bg-brand-600" : "bg-slate-700"}`}
      >
        <span
          className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform duration-200 ${checked ? "translate-x-5" : "translate-x-0"}`}
        />
      </button>
    </label>
  );
}

export default function SettingsPage() {
  const [settings, setSettings] = useState<AppSettings>(DEFAULTS);
  const [saved, setSaved] = useState(false);

  function set<K extends keyof AppSettings>(key: K, value: AppSettings[K]) {
    setSettings((prev) => ({ ...prev, [key]: value }));
    setSaved(false);
  }

  function handleSave() {
    // In a real app: persist to localStorage or backend
    localStorage.setItem("uif_settings", JSON.stringify(settings));
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  }

  function handleReset() {
    setSettings(DEFAULTS);
    setSaved(false);
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <SectionHeader
        title="Settings"
        subtitle="Configure API endpoints and model parameters"
      />

      {/* ── Connection ─────────────────────────────────────────────────── */}
      <SectionCard title="Connection">
        <div>
          <label className="block text-xs text-slate-500 mb-1">
            API Base URL
          </label>
          <input
            className="input"
            value={settings.apiUrl}
            onChange={(e) => set("apiUrl", e.target.value)}
          />
        </div>
        <div>
          <label className="block text-xs text-slate-500 mb-1">
            WebSocket URL
          </label>
          <input
            className="input"
            value={settings.wsUrl}
            onChange={(e) => set("wsUrl", e.target.value)}
          />
        </div>
        <div className="flex items-center gap-3">
          <a
            href={`${settings.apiUrl}/docs`}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-secondary text-xs flex items-center gap-1.5"
          >
            <ExternalLink size={12} /> Open API Docs
          </a>
          <a
            href={`${settings.apiUrl}/graphql`}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-secondary text-xs flex items-center gap-1.5"
          >
            <ExternalLink size={12} /> GraphiQL
          </a>
        </div>
      </SectionCard>

      {/* ── Display ────────────────────────────────────────────────────── */}
      <SectionCard title="Display">
        <div>
          <label className="block text-xs text-slate-500 mb-1">
            Default City
          </label>
          <input
            className="input"
            value={settings.defaultCity}
            onChange={(e) => set("defaultCity", e.target.value)}
          />
        </div>
        <div>
          <label className="block text-xs text-slate-500 mb-1">
            Auto-refresh Interval (seconds)
          </label>
          <input
            type="number"
            min={5}
            max={60}
            className="input w-32"
            value={settings.autoRefreshInterval}
            onChange={(e) =>
              set("autoRefreshInterval", parseInt(e.target.value))
            }
          />
        </div>
        <Toggle
          label="Show Confidence Interval"
          description="Display price bounds on prediction results"
          checked={settings.showConfidenceInterval}
          onChange={(v) => set("showConfidenceInterval", v)}
        />
      </SectionCard>

      {/* ── Model ──────────────────────────────────────────────────────── */}
      <SectionCard title="Model Training">
        <div>
          <label className="block text-xs text-slate-500 mb-1">
            Optuna Trials
          </label>
          <input
            type="number"
            min={5}
            max={500}
            className="input w-32"
            value={settings.nOptunTrials}
            onChange={(e) => set("nOptunTrials", parseInt(e.target.value))}
          />
          <p className="text-xs text-slate-600 mt-1">
            More trials = better model, longer training time
          </p>
        </div>
        <Toggle
          label="Transfer Learning"
          description="Use multi-city knowledge transfer to improve predictions in data-sparse cities"
          checked={settings.transferLearningEnabled}
          onChange={(v) => set("transferLearningEnabled", v)}
        />
        <Toggle
          label="NLP Features (DistilBERT)"
          description="Extract text embeddings from listing descriptions. Requires GPU for acceptable speed."
          checked={settings.nlpEnabled}
          onChange={(v) => set("nlpEnabled", v)}
        />
      </SectionCard>

      {/* ── About ──────────────────────────────────────────────────────── */}
      <SectionCard title="About">
        <div className="grid grid-cols-2 gap-3 text-sm">
          {[
            { label: "Version", value: "2.0.0" },
            { label: "Framework", value: "React 18 + Vite" },
            { label: "Backend", value: "FastAPI + Polars" },
            { label: "Models", value: "XGBoost · LightGBM · CatBoost" },
          ].map(({ label, value }) => (
            <div key={label}>
              <p className="text-xs text-slate-600">{label}</p>
              <p className="text-slate-300 font-medium">{value}</p>
            </div>
          ))}
        </div>
      </SectionCard>

      {/* ── Actions ────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-3">
        <button
          onClick={handleSave}
          className="btn-primary flex items-center gap-2"
        >
          <Save size={15} />
          {saved ? "Saved!" : "Save Settings"}
        </button>
        <button
          onClick={handleReset}
          className="btn-secondary flex items-center gap-2"
        >
          <RotateCcw size={15} /> Reset Defaults
        </button>
      </div>
    </div>
  );
}
