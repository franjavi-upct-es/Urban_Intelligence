// frontend/src/components/ui/index.tsx
// Urban Intelligence Framework v2.0.0
// Reusable primitive UI components

import clsx from "clsx";
import { Loader2, AlertCircle, InboxIcon } from "lucide-react";

// —— StatCard —————————————————————————————————————————————————————————————————

interface StatCardProps {
  label: string;
  value: string | number | null | undefined;
  sub?: string;
  icon?: React.ReactNode;
  trend?: { value: number; label: string };
  className?: string;
}

export function StatCard({
  label,
  value,
  sub,
  icon,
  trend,
  className,
}: StatCardProps) {
  const isPositive = (trend?.value ?? 0) >= 0;
  return (
    <div className={clsx("stat-card", className)}>
      <div className="flex items-start justify-between">
        <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">
          {label}
        </span>
        {icon && <span className="text-slate-500">{icon}</span>}
      </div>
      <div className="text-2xl font-bold text-slate-100 mt-1">
        {value ?? <span className="text-slate-600">—</span>}
      </div>
      {sub && <p className="text-xs text-slate-500">{sub}</p>}
      {trend && (
        <div
          className={clsx(
            "flex items-center gap-1 text-xs font-medium mt-1",
            isPositive ? "text-green-400" : "text-red-400",
          )}
        >
          <span>{isPositive ? "▲" : "▼"}</span>
          <span>
            {Math.abs(trend.value).toFixed(1)}% {trend.label}
          </span>
        </div>
      )}
    </div>
  );
}

// —— Spinner ——————————————————————————————————————————————————————————————————

export function Spinner({
  size = 20,
  className,
}: {
  size?: number;
  className?: string;
}) {
  return (
    <Loader2
      size={size}
      className={clsx("animate-spin text-brand-400", className)}
    />
  );
}

export function FullPageSpinner({
  message = "Loading...",
}: {
  message?: string;
}) {
  return (
    <div className="flex flex-col items-center justify-center h-64 gap-3">
      <Spinner size={32} />
      <p className="text-sm text-slate-500">{message}</p>
    </div>
  );
}

// —— ErrorBanner ——————————————————————————————————————————————————————————————

export function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="flex items-center gap-3 p-4 rounded-lg bg-red-900/30 border border-red-700/50 text-red-300">
      <AlertCircle size={18} className="shrink-0" />
      <p className="text-sm">{message}</p>
    </div>
  );
}

// —— EmptyState ———————————————————————————————————————————————————————————————

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 gap-3 text-center">
      <InboxIcon size={40} className="text-slate-700" />
      <div>
        <p className="font-medium text-slate-400">{title}</p>
        {description && (
          <p className="text-sm text-slate-600 mt-1">{description}</p>
        )}
      </div>
      {action}
    </div>
  );
}

// —— Badge ————————————————————————————————————————————————————————————————————

type BadgeVariant = "blue" | "green" | "yellow" | "red" | "gray";

export function Badge({
  children,
  variant = "gray",
}: {
  children: React.ReactNode;
  variant?: BadgeVariant;
}) {
  return <span className={`badge-${variant}`}>{children}</span>;
}

// —— SectionHeader ————————————————————————————————————————————————————————————

export function SectionHeader({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between mb-6">
      <div>
        <h2 className="text-xl font-bold text-slate-100">{title}</h2>
        {subtitle && (
          <p className="text-sm text-slate-500 mt-0.5">{subtitle}</p>
        )}
      </div>
      {action}
    </div>
  );
}
// ── ProgressBar ───────────────────────────────────────────────────────────

export function ProgressBar({
  value,
  max = 100,
  color = "brand",
}: {
  value: number;
  max?: number;
  color?: "brand" | "green" | "yellow" | "red";
}) {
  const pct = Math.min(100, (value / max) * 100);
  const colorMap = {
    brand: "bg-brand-500",
    green: "bg-green-500",
    yellow: "bg-yellow-500",
    red: "bg-red-500",
  };
  return (
    <div className="h-1.5 bg-surface-700 rounded-full overflow-hidden">
      <div
        className={clsx(
          "h-full rounded-full transition-all duration-500",
          colorMap[color],
        )}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

// ── Table ─────────────────────────────────────────────────────────────────

export function Table({
  headers,
  rows,
  className,
}: {
  headers: string[];
  rows: (string | number | React.ReactNode)[][];
  className?: string;
}) {
  return (
    <div
      className={clsx(
        "overflow-x-auto rounded-lg border border-slate-700/50",
        className,
      )}
    >
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-700/50 bg-surface-900/50">
            {headers.map((h) => (
              <th
                key={h}
                className="text-left px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr
              key={i}
              className="border-b border-slate-700/30 hover:bg-surface-700/30 transition-colors"
            >
              {row.map((cell, j) => (
                <td key={j} className="px-4 py-3 text-slate-300">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
