// frontend/src/utils/index.ts
// Urban Intelligence Framework - Utility Functions

import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

// =============================================================================
// CSS Class Utilities
// =============================================================================

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

// =============================================================================
// Formatting Utilities
// =============================================================================

export function formatCurrency(value: number, currency = "USD"): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatNumber(value: number, decimals = 2): string {
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

export function formatPercentage(value: number, decimals = 1): string {
  return `${formatNumber(value, decimals)}%`;
}

export function formatDate(date: string | Date): string {
  const d = typeof date === "string" ? new Date(date) : date;
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(d);
}

export function formatDateTime(date: string | Date): string {
  const d = typeof date === "string" ? new Date(date) : date;
  return new Intl.DateTimeFormat("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(d);
}

export function formatRelativeTime(date: string | Date): string {
  const d = typeof date === "string" ? new Date(date) : date;
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffSecs = Math.floor(diffMs / 1000);
  const diffMins = Math.floor(diffSecs / 60);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSecs < 60) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return formatDate(d);
}

// =============================================================================
// Validation Utilities
// =============================================================================

export function isValidLatitude(lat: number): boolean {
  return lat >= -90 && lat <= 90;
}

export function isValidLongitude(lng: number): boolean {
  return lng >= -180 && lng <= 180;
}

export function isValidPrice(price: number): boolean {
  return price > 0 && price < 100000;
}

// =============================================================================
// Color Utilities
// =============================================================================

export function getSeverityColor(severity: string): string {
  const colors: Record<string, string> = {
    none: "text-green-600 bg-green-100",
    low: "text-blue-600 bg-blue-100",
    medium: "text-yellow-600 bg-yellow-100",
    high: "text-orange-600 bg-orange-100",
    critical: "text-red-600 bg-red-100",
    info: "text-blue-600 bg-blue-100",
    warning: "text-yellow-600 bg-yellow-100",
    error: "text-red-600 bg-red-100",
  };
  return colors[severity] || "text-gray-600 bg-gray-100";
}

export function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    healthy: "text-green-600",
    degraded: "text-yellow-600",
    unhealthy: "text-red-600",
    available: "text-green-600",
    downloading: "text-blue-600",
    cached: "text-green-600",
    error: "text-red-600",
    unknown: "text-gray-600",
    running: "text-green-600",
    paused: "text-yellow-600",
    completed: "text-blue-600",
    draft: "text-gray-600",
  };
  return colors[status] || "text-gray-600";
}

// =============================================================================
// Data Utilities
// =============================================================================

export function calculatePercentile(
  values: number[],
  percentile: number,
): number {
  const sorted = [...values].sort((a, b) => a - b);
  const index = Math.ceil((percentile / 100) * sorted.length) - 1;
  return sorted[Math.max(0, index)];
}

export function groupBy<T>(array: T[], key: keyof T): Record<string, T[]> {
  return array.reduce(
    (result, item) => {
      const groupKey = String(item[key]);
      if (!result[groupKey]) {
        result[groupKey] = [];
      }
      result[groupKey].push(item);
      return result;
    },
    {} as Record<string, T[]>,
  );
}

// =============================================================================
// Debounce & Throttle
// =============================================================================

export function debounce<T extends (...args: Parameters<T>) => void>(
  func: T,
  wait: number,
): (...args: Parameters<T>) => void {
  let timeoutId: ReturnType<typeof setTimeout> | null = null;

  return (...args: Parameters<T>) => {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }
    timeoutId = setTimeout(() => func(...args), wait);
  };
}

export function throttle<T extends (...args: Parameters<T>) => void>(
  func: T,
  limit: number,
): (...args: Parameters<T>) => void {
  let inThrottle = false;

  return (...args: Parameters<T>) => {
    if (!inThrottle) {
      func(...args);
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
    }
  };
}

// =============================================================================
// Local Storage Utilities
// =============================================================================

export function getStoredValue<T>(key: string, defaultValue: T): T {
  try {
    const stored = localStorage.getItem(key);
    return stored ? JSON.parse(stored) : defaultValue;
  } catch {
    return defaultValue;
  }
}

export function setStoredValue<T>(key: string, value: T): void {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch (error) {
    console.error("Failed to store value:", error);
  }
}
