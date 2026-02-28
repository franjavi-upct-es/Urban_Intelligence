// frontend/src/pages/Dashboard.tsx
// Urban Intelligence Framework - Dashboard Page

import {
  TrendingUp,
  Map,
  Activity,
  DollarSign,
  AlertTriangle,
  CheckCircle,
} from "lucide-react";
import {
  Card,
  CardHeader,
  CardContent,
  CardTitle,
  StatCard,
  Badge,
} from "@/components/ui";
import {
  SimpleAreaChart,
  SimpleBarChart,
  SimplePieChart,
} from "@/components/charts";
import {
  useCities,
  useCityStatistics,
  usePerformanceMetrics,
  useHealth,
} from "@/hooks";
import { formatCurrency, formatNumber, cn, getStatusColor } from "@/utils";

export function Dashboard() {
  const { data: cities, isLoading: citiesLoading } = useCities(true);
  const { data: stats } = useCityStatistics("madrid");
  const { data: performance, isLoading: perfLoading } = usePerformanceMetrics();
  const { data: health } = useHealth();

  // Mock data for charts
  const priceHistory = Array.from({ length: 30 }, (_, i) => ({
    day: `Day ${i + 1}`,
    price: 100 + Math.random() * 50 + i * 0.5,
  }));

  const roomTypeData = [
    { name: "Entire home", value: 60 },
    { name: "Private room", value: 30 },
    { name: "Shared room", value: 7 },
    { name: "Hotel room", value: 3 },
  ];

  const neighborhoodData = [
    { name: "Centro", count: 2500 },
    { name: "Salamanca", count: 1800 },
    { name: "Chamberí", count: 1500 },
    { name: "Retiro", count: 1200 },
    { name: "Chamartín", count: 1000 },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Dashboard
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            Overview of your price prediction system
          </p>
        </div>
        <Badge variant={health?.status === "healthy" ? "success" : "warning"}>
          System {health?.status || "Unknown"}
        </Badge>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Cities"
          value={cities?.length || 0}
          icon={<Map className="w-6 h-6" />}
          loading={citiesLoading}
        />
        <StatCard
          title="Avg Price"
          value={stats ? formatCurrency(stats.price_mean) : "-"}
          change={3.2}
          icon={<DollarSign className="w-6 h-6" />}
          loading={!stats}
        />
        <StatCard
          title="Predictions Today"
          value={formatNumber(performance?.prediction_count || 0, 0)}
          icon={<TrendingUp className="w-6 h-6" />}
          loading={perfLoading}
        />
        <StatCard
          title="Model MAE"
          value={performance ? `$${formatNumber(performance.mae, 2)}` : "-"}
          icon={<Activity className="w-6 h-6" />}
          loading={perfLoading}
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <SimpleAreaChart
          data={priceHistory}
          xKey="day"
          yKey="price"
          title="Average Price Trend (30 Days)"
        />
        <SimplePieChart data={roomTypeData} title="Room Type Distribution" />
      </div>

      {/* Bottom Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Top Neighborhoods */}
        <div className="lg:col-span-2">
          <SimpleBarChart
            data={neighborhoodData}
            xKey="name"
            yKey="count"
            title="Top Neighborhoods by Listings"
          />
        </div>

        {/* System Status */}
        <Card>
          <CardHeader>
            <CardTitle>System Status</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <StatusItem
              label="API Server"
              status={health?.status || "unknown"}
              icon={<CheckCircle className="w-4 h-4" />}
            />
            <StatusItem
              label="ML Model"
              status={health?.model_loaded ? "healthy" : "unhealthy"}
              icon={<Activity className="w-4 h-4" />}
            />
            <StatusItem
              label="Database"
              status={health?.database_connected ? "healthy" : "unhealthy"}
              icon={<CheckCircle className="w-4 h-4" />}
            />
            <StatusItem
              label="Data Freshness"
              status="healthy"
              icon={<CheckCircle className="w-4 h-4" />}
            />
          </CardContent>
        </Card>
      </div>

      {/* Recent Alerts */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Recent Alerts</CardTitle>
          <Badge variant="info">3 Active</Badge>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <AlertItem
              level="warning"
              message="Data drift detected in 'bedrooms' feature"
              time="2 hours ago"
            />
            <AlertItem
              level="info"
              message="Model retraining completed successfully"
              time="5 hours ago"
            />
            <AlertItem
              level="error"
              message="Weather API rate limit reached"
              time="1 day ago"
            />
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// Status Item Component
function StatusItem({
  label,
  status,
  icon,
}: {
  label: string;
  status: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between py-2 border-b border-gray-100 dark:border-gray-700 last:border-0">
      <div className="flex items-center gap-2 text-gray-600 dark:text-gray-300">
        {icon}
        <span>{label}</span>
      </div>
      <span className={cn("font-medium capitalize", getStatusColor(status))}>
        {status}
      </span>
    </div>
  );
}

// Alert Item Component
function AlertItem({
  level,
  message,
  time,
}: {
  level: "info" | "warning" | "error";
  message: string;
  time: string;
}) {
  const icons = {
    info: <CheckCircle className="w-4 h-4 text-blue-500" />,
    warning: <AlertTriangle className="w-4 h-4 text-yellow-500" />,
    error: <AlertTriangle className="w-4 h-4 text-red-500" />,
  };

  return (
    <div className="flex items-start gap-3 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
      {icons[level]}
      <div className="flex-1">
        <p className="text-sm text-gray-900 dark:text-white">{message}</p>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">{time}</p>
      </div>
    </div>
  );
}

export default Dashboard;
