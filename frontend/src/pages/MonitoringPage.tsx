// frontend/src/pages/MonitoringPage.tsx
// Urban Intelligence Framework v2.0.0
// Live model monitoring dashboard — snapshots, alerts, and metrics

import { useState } from "react";
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  XCircle,
  RefreshCw,
} from "lucide-react";
import { useMonitoringSnapshot, useAllAlerts, useResolveAlert } from "@/hooks";
import {
  SectionHeader,
  StatCard,
  Badge,
  FullPageSpinner,
  EmptyState,
  ProgressBar,
} from "@/components/ui";
import { MetricsLineChart } from "@/components/charts";
import clsx from "clsx";

const CITIES = ["london", "paris", "barcelona", "new-york", "amsterdam"];

// ── Alert card ────────────────────────────────────────────────────────────

function AlertCard({
  alert,
  onResolve,
}: {
  alert: {
    alert_id: string;
    city_id?: string;
    metric: string;
    severity: string;
    message: string;
    current_value: number;
  };
  onResolve: (id: string) => void;
}) {
  return (
    <div
      className={clsx(
        "flex items-start justify-between p-4 rounded-lg border",
        alert.severity === "critical"
          ? "bg-red-900/20 border-red-700/50"
          : "bg-yellow-900/20 border-yellow-700/50",
      )}
    >
      <div className="flex items-start gap-3">
        {alert.severity === "critical" ? (
          <XCircle size={16} className="text-red-400 mt-0.5 shrink-0" />
        ) : (
          <AlertTriangle
            size={16}
            className="text-yellow-400 mt-0.5 shrink-0"
          />
        )}
        <div>
          <p className="text-sm font-medium text-slate-200">{alert.message}</p>
          <p className="text-xs text-slate-500 mt-0.5">
            {alert.city_id && <span className="mr-2">{alert.city_id}</span>}
            Value:{" "}
            <span className="font-mono">{alert.current_value.toFixed(4)}</span>
          </p>
        </div>
      </div>
      <button
        onClick={() => onResolve(alert.alert_id)}
        className="text-xs text-slate-500 hover:text-slate-300 flex items-center gap-1 ml-4 shrink-0"
      >
        <CheckCircle size={13} /> Resolve
      </button>
    </div>
  );
}

// ── City snapshot card ────────────────────────────────────────────────────

function CitySnapshotCard({ cityId }: { cityId: string }) {
  const { data: snap, isLoading } = useMonitoringSnapshot(cityId);

  if (isLoading)
    return (
      <div className="card p-5 flex items-center justify-center h-40">
        <RefreshCw size={18} className="animate-spin text-slate-600" />
      </div>
    );

  if (!snap) return null;

  return (
    <div className="card p-5 space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="font-semibold text-slate-200 capitalize">{cityId}</h4>
        <Badge variant={snap.active_alerts.length > 0 ? "red" : "green"}>
          {snap.active_alerts.length > 0
            ? `${snap.active_alerts.length} alerts`
            : "Healthy"}
        </Badge>
      </div>

      <div className="grid grid-cols-2 gap-3 text-sm">
        {[
          {
            label: "RMSE",
            value: snap.rmse != null ? snap.rmse.toFixed(4) : "—",
          },
          { label: "MAE", value: snap.mae != null ? snap.mae.toFixed(4) : "—" },
          { label: "R²", value: snap.r2 != null ? snap.r2.toFixed(3) : "—" },
          {
            label: "Latency",
            value:
              snap.avg_latency_ms != null
                ? `${snap.avg_latency_ms.toFixed(1)}ms`
                : "—",
          },
        ].map(({ label, value }) => (
          <div key={label}>
            <p className="text-xs text-slate-600">{label}</p>
            <p className="font-mono font-medium text-slate-300">{value}</p>
          </div>
        ))}
      </div>

      <div>
        <div className="flex justify-between text-xs text-slate-600 mb-1">
          <span>Error rate</span>
          <span>{(snap.error_rate * 100).toFixed(1)}%</span>
        </div>
        <ProgressBar
          value={snap.error_rate * 100}
          color={
            snap.error_rate > 0.05
              ? "red"
              : snap.error_rate > 0.01
                ? "yellow"
                : "green"
          }
        />
      </div>

      <div className="text-xs text-slate-600 flex justify-between">
        <span>Predictions: {snap.n_predictions.toLocaleString()}</span>
        <span>Req/min: {snap.request_rate.toFixed(1)}</span>
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────

// Build a minimal mock time-series for the metrics chart
function mockMetricsSeries() {
  return Array.from({ length: 20 }, (_, i) => ({
    date: `T-${20 - i}`,
    rmse: 0.18 + Math.random() * 0.06,
    mae: 0.12 + Math.random() * 0.04,
  }));
}

export default function MonitoringPage() {
  const { data: alertsData, isLoading: alertsLoading } = useAllAlerts();
  const resolve = useResolveAlert();
  const [metricsData] = useState(mockMetricsSeries);

  const alerts = alertsData?.alerts ?? [];

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Monitoring"
        subtitle="Live model health across all deployed cities"
      />

      {/* ── Top-line alert count ──────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard
          label="Active Alerts"
          value={alertsData?.total ?? 0}
          icon={<AlertTriangle size={18} />}
        />
        <StatCard
          label="Cities Monitored"
          value={CITIES.length}
          icon={<Activity size={18} />}
        />
        <StatCard
          label="Auto-refresh"
          value="10s"
          sub="Snapshots refresh automatically"
        />
      </div>

      {/* ── Alerts list ───────────────────────────────────────────────── */}
      <div className="card p-5">
        <h3 className="text-sm font-semibold text-slate-300 mb-4">
          Active Alerts
        </h3>
        {alertsLoading ? (
          <FullPageSpinner message="Loading alerts…" />
        ) : alerts.length === 0 ? (
          <EmptyState
            title="No active alerts"
            description="All models are operating within thresholds."
          />
        ) : (
          <div className="space-y-2">
            {alerts.map((alert) => (
              <AlertCard
                key={alert.alert_id}
                alert={alert}
                onResolve={(id) => resolve.mutate(id)}
              />
            ))}
          </div>
        )}
      </div>

      {/* ── Metrics trend ─────────────────────────────────────────────── */}
      <div className="card p-5">
        <h3 className="text-sm font-semibold text-slate-300 mb-4">
          Metrics Trend (mock)
        </h3>
        <MetricsLineChart
          data={metricsData}
          lines={[
            { key: "rmse", label: "RMSE", color: "#3b82f6" },
            { key: "mae", label: "MAE", color: "#10b981" },
          ]}
          height={200}
        />
      </div>

      {/* ── Per-city snapshots ─────────────────────────────────────────── */}
      <div>
        <h3 className="text-sm font-semibold text-slate-300 mb-4">
          City Snapshots
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {CITIES.map((city) => (
            <CitySnapshotCard key={city} cityId={city} />
          ))}
        </div>
      </div>
    </div>
  );
}
