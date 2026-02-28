// frontend/src/components/charts/index.tsx
// Urban Intelligence Framework - Chart Components

import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { Card, CardHeader, CardContent, CardTitle } from "@/components/ui";

// =============================================================================
// Color Palette
// =============================================================================

const COLORS = {
  primary: "#0ea5e9",
  secondary: "#8b5cf6",
  accent: "#d946ef",
  success: "#22c55e",
  warning: "#f59e0b",
  error: "#ef4444",
  gray: "#6b7280",
};

const PIE_COLORS = [
  "#0ea5e9",
  "#8b5cf6",
  "#d946ef",
  "#22c55e",
  "#f59e0b",
  "#ef4444",
];

// =============================================================================
// Line Chart
// =============================================================================

interface LineChartProps {
  data: Array<Record<string, unknown>>;
  xKey: string;
  yKey: string;
  title?: string;
  color?: string;
  height?: number;
}

export function SimpleLineChart({
  data,
  xKey,
  yKey,
  title,
  color = COLORS.primary,
  height = 300,
}: LineChartProps) {
  return (
    <Card>
      {title && (
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
      )}
      <CardContent>
        <ResponsiveContainer width="100%" height={height}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey={xKey}
              tick={{ fontSize: 12, fill: "#6b7280" }}
              tickLine={false}
              axisLine={{ stroke: "#e5e7eb" }}
            />
            <YAxis
              tick={{ fontSize: 12, fill: "#6b7280" }}
              tickLine={false}
              axisLine={{ stroke: "#e5e7eb" }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "#fff",
                border: "1px solid #e5e7eb",
                borderRadius: "8px",
                boxShadow: "0 4px 6px -1px rgb(0 0 0 / 0.1)",
              }}
            />
            <Line
              type="monotone"
              dataKey={yKey}
              stroke={color}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

// =============================================================================
// Area Chart
// =============================================================================

interface AreaChartProps {
  data: Array<Record<string, unknown>>;
  xKey: string;
  yKey: string;
  title?: string;
  color?: string;
  height?: number;
  gradient?: boolean;
}

export function SimpleAreaChart({
  data,
  xKey,
  yKey,
  title,
  color = COLORS.primary,
  height = 300,
  gradient = true,
}: AreaChartProps) {
  return (
    <Card>
      {title && (
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
      )}
      <CardContent>
        <ResponsiveContainer width="100%" height={height}>
          <AreaChart data={data}>
            <defs>
              <linearGradient id="colorGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={color} stopOpacity={0.3} />
                <stop offset="95%" stopColor={color} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey={xKey}
              tick={{ fontSize: 12, fill: "#6b7280" }}
              tickLine={false}
              axisLine={{ stroke: "#e5e7eb" }}
            />
            <YAxis
              tick={{ fontSize: 12, fill: "#6b7280" }}
              tickLine={false}
              axisLine={{ stroke: "#e5e7eb" }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "#fff",
                border: "1px solid #e5e7eb",
                borderRadius: "8px",
              }}
            />
            <Area
              type="monotone"
              dataKey={yKey}
              stroke={color}
              strokeWidth={2}
              fill={gradient ? "url(#colorGradient)" : color}
              fillOpacity={gradient ? 1 : 0.1}
            />
          </AreaChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

// =============================================================================
// Bar Chart
// =============================================================================

interface BarChartProps {
  data: Array<Record<string, unknown>>;
  xKey: string;
  yKey: string;
  title?: string;
  color?: string;
  height?: number;
  horizontal?: boolean;
}

export function SimpleBarChart({
  data,
  xKey,
  yKey,
  title,
  color = COLORS.primary,
  height = 300,
  horizontal = false,
}: BarChartProps) {
  return (
    <Card>
      {title && (
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
      )}
      <CardContent>
        <ResponsiveContainer width="100%" height={height}>
          <BarChart data={data} layout={horizontal ? "vertical" : "horizontal"}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            {horizontal ? (
              <>
                <XAxis type="number" tick={{ fontSize: 12, fill: "#6b7280" }} />
                <YAxis
                  type="category"
                  dataKey={xKey}
                  tick={{ fontSize: 12, fill: "#6b7280" }}
                  width={100}
                />
              </>
            ) : (
              <>
                <XAxis
                  dataKey={xKey}
                  tick={{ fontSize: 12, fill: "#6b7280" }}
                  tickLine={false}
                />
              </>
            )}
            <Tooltip
              contentStyle={{
                backgroundColor: "#fff",
                border: "1px solid #e5e7eb",
                borderRadius: "8px",
              }}
            />
            <Bar dataKey={yKey} fill={color} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

// =============================================================================
// Pie Chart
// =============================================================================

interface PieChartProps {
  data: Array<{ name: string; value: number }>;
  title?: string;
  height?: number;
}

export function SimplePieChart({ data, title, height = 300 }: PieChartProps) {
  return (
    <Card>
      {title && (
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
      )}
      <CardContent>
        <ResponsiveContainer width="100%" height={height}>
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={60}
              outerRadius={100}
              paddingAngle={2}
              dataKey="value"
              label={({ name, percent }) =>
                `${name} ${(percent * 100).toFixed(0)}%`
              }
              labelLine={false}
            >
              {data.map((_, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={PIE_COLORS[index % PIE_COLORS.length]}
                />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                backgroundColor: "#fff",
                border: "1px solid #e5e7eb",
                borderRadius: "8px",
              }}
            />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

// =============================================================================
// Multi-Line Chart
// =============================================================================

interface MultiLineChartProps {
  data: Array<Record<string, unknown>>;
  xKey: string;
  lines: Array<{ key: string; color: string; name: string }>;
  title?: string;
  height?: number;
}

export function MultiLineChart({
  data,
  xKey,
  lines,
  title,
  height = 300,
}: MultiLineChartProps) {
  return (
    <Card>
      {title && (
        <CardHeader>
          <CardTitle>{title}</CardTitle>
        </CardHeader>
      )}
      <CardContent>
        <ResponsiveContainer width="100%" height={height}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis
              dataKey={xKey}
              tick={{ fontSize: 12, fill: "#6b7280" }}
              tickLine={false}
            />
            <YAxis tick={{ fontSize: 12, fill: "#6b7280" }} tickLine={false} />
            <Tooltip
              contentStyle={{
                backgroundColor: "#fff",
                border: "1px solid #e5e7eb",
                borderRadius: "8px",
              }}
            />
            <Legend />
            {lines.map((line) => (
              <Line
                key={line.key}
                type="monotone"
                dataKey={line.key}
                name={line.name}
                stroke={line.color}
                strokeWidth={2}
                dot={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

// =============================================================================
// Feature Importance Chart
// =============================================================================

interface FeatureImportanceChartProps {
  data: Record<string, number>;
  title?: string;
  height?: number;
  limit?: number;
}

export function FeatureImportanceChart({
  data,
  title = "Feature Importance",
  height = 400,
  limit = 10,
}: FeatureImportanceChartProps) {
  const chartData = Object.entries(data)
    .sort(([, a], [, b]) => b - a)
    .slice(0, limit)
    .map(([feature, importance]) => ({
      feature: feature.length > 20 ? feature.slice(0, 20) + "..." : feature,
      importance: importance * 100,
    }));

  return (
    <SimpleBarChart
      data={chartData}
      xKey="feature"
      yKey="importance"
      title={title}
      color={COLORS.primary}
      height={height}
      horizontal
    />
  );
}

export { COLORS };
