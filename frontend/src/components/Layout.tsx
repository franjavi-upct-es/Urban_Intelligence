// frontend/src/components/Layout.tsx
// Urban Intelligence Framework v2.0.0
// Main layout component with sidebar navigation

import { useState } from "react";
import { Outlet, NavLink, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  TrendingUp,
  Map,
  BarChart3,
  FlaskConical,
  Activity,
  Settings,
  Menu,
  X,
  Brain,
  ChevronRight,
} from "lucide-react";
import clsx from "clsx";

const NAV_ITEMS = [
  { path: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { path: "/predict", label: "Predict", icon: TrendingUp },
  { path: "/cities", label: "Cities", icon: Map },
  { path: "/analytics", label: "Analytics", icon: BarChart3 },
  { path: "/experiments", label: "Experiments", icon: FlaskConical },
  { path: "/monitoring", label: "Monitoring", icon: Activity },
  { path: "/settings", label: "Settings", icon: Settings },
];

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();

  const currentPage = NAV_ITEMS.find((items) =>
    location.pathname.startsWith(items.path),
  );

  return (
    <div className="flex h-screen bg-surface-900 overflow-hidden">
      {/* —— Mobile overlay ————————————————————————————————————————————— */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-20 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* —— Sidebar ———————————————————————————————————————————————————— */}
      <aside
        className={clsx(
          "fixed inset-y-0 left-0 z-30 w-64 bg-surface-800 border-r border-slate-700/50",
          "flex flex-col transition-transform duration-300 ease-in-out",
          "lg:relative lg:translate-x-0",
          sidebarOpen ? "translate-x-0" : "-translate-x-full",
        )}
      >
        {/* Logo */}
        <div className="flex items-center gap-3 px-5 py-5 border-b border-slate-700/50">
          <div className="p-2 bg-brand-600 rounded-lg">
            <Brain size={20} className="text-white" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-slate-100 leading-tight">
              Urban Intelligence
            </h1>
            <p className="text-xs text-slate-500">v2.0.0</p>
          </div>
          <button
            className="ml-auto lg:hidden text-slate-400 hover:text-slate-200"
            onClick={() => setSidebarOpen(false)}
          >
            <X size={18} />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
          {NAV_ITEMS.map(({ path, label, icon: Icon }) => (
            <NavLink
              key={path}
              to={path}
              onClick={() => setSidebarOpen(false)}
              className={({ isActive }) =>
                clsx(
                  "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors duration-150",
                  isActive
                    ? "bg-brand-600/20 text-brand-400 border border-brand-500/30"
                    : "text-slate-400 hover:text-slate-200 hover:bg-surface-700",
                )
              }
            >
              <Icon size={17} />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-slate-700/50">
          <p className="text-xs text-slate-600 text-center">
            © 2026 Urban Intelligence
          </p>
        </div>
      </aside>

      {/* —— Main content —————————————————————————————————————————————————————— */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top bar */}
        <header className="flex items-center gap-4 px-5 py-4 border-b border-slate-700/50 bg-surface-800/50 backdrop-blur-sm shrink-0">
          <button
            className="lg:hidden text-slate-400 hover:text-slate-200"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu size={20} />
          </button>

          {/* Breadcrumb */}
          <div className="flex items-center gap-2 text-sm">
            <span className="text-slate-500">Urban Intelligence</span>
            <ChevronRight size={14} className="text-slate-600" />
            <span className="text-slate-200 font-medium">
              {currentPage?.label ?? "Page"}
            </span>
          </div>
        </header>
        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-5 lg:p-6 animate-fade-in">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
