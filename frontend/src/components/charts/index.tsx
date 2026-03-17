// frontend/src/components/charts/index.tsx
// Urban Intelligence Framework v2.0.0
// Recharts-based chart components with dark-theme defaults

import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  LineChart,
  Line,
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

const GRID_COLOR = "#334155";
const AXIS_COLOR = "#64748b";
const TOOLTIP_STYLE = {
  backgroundColor: "#1e293b",
  border: "1px solid #334155",
  borderRadius: 8,
  color: "#f1f5f9",
  fontSize: 12,
};
const BRAND_COLORS = [
  "#3b82f6",
  "#10b981",
  "#f59e0b",
  "#ef4444",
  "#8b5cf6",
  "#06b6d4",
];

export function AreaSparkline({
  data,
  dataKey,
  color = "#3b82f6",
  height = 120,
}: {
  data: object[];
  dataKey: string;
  color?: string;
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 4, right: 0, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id={`grad-${dataKey}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={color} stopOpacity={0.3} />
            <stop offset="95%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <Area
          type="monotone"
          dataKey={dataKey}
          stroke={color}
          strokeWidth={2}
          fill={`url(#grad-${dataKey})`}
          dot={false}
        />
        <Tooltip contentStyle={TOOLTIP_STYLE} />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function PriceDistributionChart({
  data,
  height = 220,
}: {
  data: { bin: string; count: number }[];
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
        <CartesianGrid
          strokeDasharray="3 3"
          stroke={GRID_COLOR}
          vertical={false}
        />
        <XAxis
          dataKey="bin"
          tick={{ fill: AXIS_COLOR, fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: AXIS_COLOR, fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip contentStyle={TOOLTIP_STYLE} cursor={{ fill: "#334155" }} />
        <Bar dataKey="count" fill="#3b82f6" radius={[3, 3, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function MetricsLineChart({
  data,
  lines,
  height = 240,
}: {
  data: object[];
  lines: { key: string; label: string; color?: string }[];
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart
        data={data}
        margin={{ top: 4, right: 8, left: -20, bottom: 0 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke={GRID_COLOR} />
        <XAxis
          dataKey="date"
          tick={{ fill: AXIS_COLOR, fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: AXIS_COLOR, fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip contentStyle={TOOLTIP_STYLE} />
        <Legend wrapperStyle={{ fontSize: 12, color: AXIS_COLOR }} />
        {lines.map(({ key, label, color }, idx) => (
          <Line
            key={key}
            type="monotone"
            dataKey={key}
            name={label}
            stroke={color ?? BRAND_COLORS[idx % BRAND_COLORS.length]}
            strokeWidth={2}
            dot={false}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}

export function RoomTypePieChart({
  data,
  height = 200,
}: {
  data: { name: string; value: number }[];
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius={50}
          outerRadius={80}
          paddingAngle={3}
          dataKey="value"
        >
          {data.map((_, idx) => (
            <Cell key={idx} fill={BRAND_COLORS[idx % BRAND_COLORS.length]} />
          ))}
        </Pie>
        <Tooltip contentStyle={TOOLTIP_STYLE} />
        <Legend wrapperStyle={{ fontSize: 12, color: AXIS_COLOR }} />
      </PieChart>
    </ResponsiveContainer>
  );
}

export function ComparisonBarChart({
  data,
  keys,
  height = 220,
}: {
  data: object[];
  keys: { key: string; label: string }[];
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
        <CartesianGrid
          strokeDasharray="3 3"
          stroke={GRID_COLOR}
          vertical={false}
        />
        <XAxis
          dataKey="name"
          tick={{ fill: AXIS_COLOR, fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: AXIS_COLOR, fontSize: 11 }}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip contentStyle={TOOLTIP_STYLE} />
        <Legend wrapperStyle={{ fontSize: 12, color: AXIS_COLOR }} />
        {keys.map(({ key, label }, idx) => (
          <Bar
            key={key}
            dataKey={key}
            name={label}
            fill={BRAND_COLORS[idx % BRAND_COLORS.length]}
            radius={[3, 3, 0, 0]}
          />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}
