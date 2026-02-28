// frontend/src/pages/Monitoring.tsx
// Urban Intelligence Framework - Monitoring Dashboard

import { useState } from "react";
import {
  Activity,
  AlertTriangle,
  TrendingUp,
  Clock,
  RefreshCw,
} from "lucide-react";
import {
  Card,
  CardHeader,
  CardContent,
  CardTitle,
  Button,
  Badge,
  StatCard,
} from "@/components/ui";
import {
  SimpleLineChart,
  MultiLineChart,
  SimpleBarChart,
} from "@/components/charts";
import {
  usePerformanceMetrics,
  useDriftReport,
  useRealtimeMetrics,
} from "@/hooks";
import { formatNumber, formatPercentage, cn } from "@/utils";

export function Monitoring() {
  const [autoRefresh, setAutoRefresh] = useState(true);
  const {
    data: performance,
    isLoading: perfLoading,
    refetch,
  } = usePerformanceMetrics();
  const { data: drift, isLoading: driftLoading } = useDriftReport();
  const realtimeMetrics = useRealtimeMetrics();

  // Mock time series data
  const latencyHistory = Array.from({ length: 24 }, (_, i) => ({
    hour: `${i}:00`,
    p50: 15 + Math.random() * 10,
    p95: 45 + Math.random() * 20,
    p99: 80 + Math.random() * 30,
  }));

  const predictionVolume = Array.from({ length: 24 }, (_, i) => ({
    hour: `${i}:00`,
    count: Math.floor(100 + Math.random() * 200),
  }));

  const errorRateHistory = Array.from({ length: 24 }, (_, i) => ({
    hour: `${i}:00`,
    rate: Math.random() * 2,
  }));

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Monitoring
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            Real-time performance metrics and drift detection
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant={autoRefresh ? "primary" : "outline"}
            size="sm"
            onClick={() => setAutoRefresh(!autoRefresh)}
          >
            <RefreshCw
              className={cn("w-4 h-4 mr-2", autoRefresh && "animate-spin")}
            />
            {autoRefresh ? "Auto-refresh ON" : "Auto-refresh OFF"}
          </Button>
          <Button variant="outline" size="sm" onClick={() => refetch()}>
            Refresh Now
          </Button>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="MAE"
          value={performance ? `$${formatNumber(performance.mae, 2)}` : "-"}
          icon={<TrendingUp className="w-6 h-6" />}
          loading={perfLoading}
        />
        <StatCard
          title="RMSE"
          value={performance ? `$${formatNumber(performance.rmse, 2)}` : "-"}
          icon={<Activity className="w-6 h-6" />}
          loading={perfLoading}
        />
        <StatCard
          title="P95 Latency"
          value={
            performance
              ? `${formatNumber(performance.latency_p95_ms, 0)}ms`
              : "-"
          }
          icon={<Clock className="w-6 h-6" />}
          loading={perfLoading}
        />
        <StatCard
          title="Error Rate"
          value={performance ? formatPercentage(performance.error_rate) : "-"}
          icon={<AlertTriangle className="w-6 h-6" />}
          loading={perfLoading}
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <MultiLineChart
          data={latencyHistory}
          xKey="hour"
          lines={[
            { key: "p50", color: "#22c55e", name: "P50" },
            { key: "p95", color: "#f59e0b", name: "P95" },
            { key: "p99", color: "#ef4444", name: "P99" },
          ]}
          title="Latency Distribution (24h)"
        />
        <SimpleBarChart
          data={predictionVolume}
          xKey="hour"
          yKey="count"
          title="Prediction Volume (24h)"
        />
      </div>

      {/* Drift Detection Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <Activity className="w-5 h-5 text-primary-600" />
                Data Drift Detection
              </CardTitle>
              {drift && (
                <Badge
                  variant={
                    drift.overall_severity === "none" ||
                    drift.overall_severity === "low"
                      ? "success"
                      : drift.overall_severity === "medium"
                        ? "warning"
                        : "error"
                  }
                >
                  {drift.overall_severity.toUpperCase()}
                </Badge>
              )}
            </CardHeader>
            <CardContent>
              {driftLoading ? (
                <div className="animate-pulse space-y-4">
                  {[1, 2, 3].map((i) => (
                    <div key={i} className="h-12 bg-gray-200 rounded" />
                  ))}
                </div>
              ) : drift ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-3 gap-4 text-center">
                    <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                      <p className="text-2xl font-bold">
                        {drift.total_features}
                      </p>
                      <p className="text-sm text-gray-500">Total Features</p>
                    </div>
                    <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                      <p className="text-2xl font-bold text-yellow-600">
                        {drift.features_with_drift}
                      </p>
                      <p className="text-sm text-gray-500">With Drift</p>
                    </div>
                    <div className="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                      <p className="text-2xl font-bold">
                        {formatPercentage(drift.drift_percentage)}
                      </p>
                      <p className="text-sm text-gray-500">Drift Rate</p>
                    </div>
                  </div>

                  {drift.recommendations.length > 0 && (
                    <div className="mt-4 p-4 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
                      <h4 className="font-medium text-yellow-800 dark:text-yellow-400 mb-2">
                        Recommendations
                      </h4>
                      <ul className="space-y-1">
                        {drift.recommendations.map((rec, i) => (
                          <li
                            key={i}
                            className="text-sm text-yellow-700 dark:text-yellow-300"
                          >
                            • {rec}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-gray-500 text-center py-8">
                  No drift data available
                </p>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Error Rate Chart */}
        <SimpleLineChart
          data={errorRateHistory}
          xKey="hour"
          yKey="rate"
          title="Error Rate (24h)"
          color="#ef4444"
          height={250}
        />
      </div>

      {/* Alerts Section */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-yellow-500" />
            Recent Alerts
          </CardTitle>
          <Button variant="ghost" size="sm">
            View All
          </Button>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <AlertRow
              level="warning"
              metric="MAE"
              value={28.5}
              threshold={25.0}
              time="15 minutes ago"
            />
            <AlertRow
              level="info"
              metric="Prediction Volume"
              value={1250}
              threshold={1000}
              time="2 hours ago"
            />
            <AlertRow
              level="error"
              metric="Error Rate"
              value={5.2}
              threshold={5.0}
              time="3 hours ago"
            />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function AlertRow({
  level,
  metric,
  value,
  threshold,
  time,
}: {
  level: "info" | "warning" | "error";
  metric: string;
  value: number;
  threshold: number;
  time: string;
}) {
  const colors = {
    info: "border-blue-200 bg-blue-50 dark:border-blue-800 dark:bg-blue-900/20",
    warning:
      "border-yellow-200 bg-yellow-50 dark:border-yellow-800 dark:bg-yellow-900/20",
    error: "border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-900/20",
  };

  return (
    <div
      className={cn(
        "flex items-center justify-between p-4 rounded-lg border",
        colors[level],
      )}
    >
      <div className="flex items-center gap-4">
        <AlertTriangle
          className={cn(
            "w-5 h-5",
            level === "info" && "text-blue-500",
            level === "warning" && "text-yellow-500",
            level === "error" && "text-red-500",
          )}
        />
        <div>
          <p className="font-medium text-gray-900 dark:text-white">{metric}</p>
          <p className="text-sm text-gray-500">
            Value: {value} (threshold: {threshold})
          </p>
        </div>
      </div>
      <span className="text-sm text-gray-500">{time}</span>
    </div>
  );
}

export default Monitoring;
