// frontend/src/pages/DashboardPage.tsx
// Urban Intelligence Framework v2.0.0
// Main dashboard — KPI cards, price trend, recent predictions

import { useMemo } from "react";
import { Brain, Map, TrendingUp, Activity, AlertTriangle } from "lucide-react";
import { useCities, useAllAlerts, usePredictionHistory } from "@/hooks";
import {
  StatCard,
  FullPageSpinner,
  ErrorBanner,
  SectionHeader,
  Badge,
} from "@/components/ui";
import { AreaSparkline, PriceDistributionChart } from "@/components/charts";
import type { DistributionBin, TimeSeriesPoint } from "@/types";

/** Build sparkline series from prediction history. */
function buildTimeSeries(
  predictions: { predicted_price: number }[],
): TimeSeriesPoint[] {
  return predictions.slice(-30).map((p, i) => ({
    date: `T-${30 - i}`,
    value: p.predicted_price,
  }));
}

/** Build a 10-bin price histogram. */
function buildDistribution(prices: number[]): DistributionBin[] {
  if (!prices.length) return [];
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const step = (max - min) / 10 || 1;
  const counts = Array(10).fill(0);
  prices.forEach((p) => {
    const idx = Math.min(9, Math.floor((p - min) / step));
    counts[idx]++;
  });
  return counts.map((count, i) => ({
    bin: `$${Math.round(min + i * step)}`,
    count,
  }));
}

export default function DashboardPage() {
  const {
    data: cities,
    isLoading: citiesLoading,
    error: citiesError,
  } = useCities();
  const { data: alertsData } = useAllAlerts();
  const { data: historyData } = usePredictionHistory(50);

  const predictions = useMemo(
    () => historyData?.history ?? [],
    [historyData?.history],
  );
  const timeSeries = useMemo(() => buildTimeSeries(predictions), [predictions]);
  const distribution = useMemo(
    () => buildDistribution(predictions.map((p) => p.predicted_price)),
    [predictions],
  );

  const cachedCities = cities?.filter((c) => c.is_cached).length ?? 0;
  const totalAlerts = alertsData?.total ?? 0;

  if (citiesLoading) return <FullPageSpinner message="Loading dashboard…" />;
  if (citiesError) return <ErrorBanner message="Failed to load city data." />;

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Dashboard"
        subtitle="Urban Intelligence Framework — real-time overview"
      />

      {/* ── KPI cards ──────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Available Cities"
          value={cities?.length ?? 0}
          sub="Inside Airbnb catalogue"
          icon={<Map size={18} />}
        />
        <StatCard
          label="Cached Cities"
          value={cachedCities}
          sub="Ready for prediction"
          icon={<Brain size={18} />}
        />
        <StatCard
          label="Predictions Logged"
          value={historyData?.total ?? 0}
          sub="All time"
          icon={<TrendingUp size={18} />}
        />
        <StatCard
          label="Active Alerts"
          value={totalAlerts}
          sub={totalAlerts > 0 ? "Requires attention" : "All clear"}
          icon={
            <AlertTriangle
              size={18}
              className={totalAlerts > 0 ? "text-yellow-400" : ""}
            />
          }
        />
      </div>

      {/* ── Charts row ─────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-slate-300 mb-4">
            Recent Prediction Trend
          </h3>
          {timeSeries.length > 0 ? (
            <AreaSparkline
              data={timeSeries}
              dataKey="value"
              color="#3b82f6"
              height={160}
            />
          ) : (
            <div className="h-40 flex items-center justify-center text-slate-600 text-sm">
              No prediction history yet
            </div>
          )}
        </div>

        <div className="card p-5">
          <h3 className="text-sm font-semibold text-slate-300 mb-4">
            Price Distribution
          </h3>
          {distribution.length > 0 ? (
            <PriceDistributionChart data={distribution} height={160} />
          ) : (
            <div className="h-40 flex items-center justify-center text-slate-600 text-sm">
              No distribution data yet
            </div>
          )}
        </div>
      </div>

      {/* ── City status table ───────────────────────────────────────────── */}
      <div className="card p-5">
        <h3 className="text-sm font-semibold text-slate-300 mb-4">
          City Status
        </h3>
        <div className="space-y-2">
          {(cities ?? []).slice(0, 8).map((city) => (
            <div
              key={city.city_id}
              className="flex items-center justify-between py-2 border-b border-slate-700/30 last:border-0"
            >
              <div>
                <span className="text-sm font-medium text-slate-200">
                  {city.name}
                </span>
                <span className="text-xs text-slate-500 ml-2">
                  {city.country}
                </span>
              </div>
              <Badge variant={city.is_cached ? "green" : "gray"}>
                {city.is_cached ? "Cached" : "Not fetched"}
              </Badge>
            </div>
          ))}
        </div>
      </div>

      {/* ── Recent predictions ──────────────────────────────────────────── */}
      {predictions.length > 0 && (
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-slate-300 mb-4">
            Recent Predictions
          </h3>
          <div className="space-y-2">
            {predictions.slice(0, 5).map((p) => (
              <div
                key={p.prediction_id}
                className="flex items-center justify-between text-sm py-2 border-b border-slate-700/30 last:border-0"
              >
                <div className="flex items-center gap-3">
                  <Activity size={14} className="text-brand-400" />
                  <span className="text-slate-400 font-mono text-xs">
                    {p.prediction_id}
                  </span>
                  <Badge variant="blue">{p.city_id}</Badge>
                </div>
                <span className="font-semibold text-slate-200">
                  ${p.predicted_price.toFixed(2)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
