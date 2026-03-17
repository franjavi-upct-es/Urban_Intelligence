// frontend/src/pages/AnalyticsPage.tsx
// Urban Intelligence Framework v2.0.0
// Analytics page — price distributions, room type breakdown, comparison charts

import { useState, useMemo } from "react";
import { useCities, useListings } from "@/hooks";
import { SectionHeader, FullPageSpinner, EmptyState } from "@/components/ui";
import {
  PriceDistributionChart,
  RoomTypePieChart,
  ComparisonBarChart,
} from "@/components/charts";

const AVAILABLE_CITIES = [
  "london",
  "paris",
  "barcelona",
  "new-york",
  "amsterdam",
];

/** Bin prices into a histogram. */
function histogram(prices: number[], bins = 12) {
  if (!prices.length) return [];
  const min = Math.min(...prices);
  const max = Math.max(...prices);
  const step = (max - min) / bins || 1;
  const counts = Array(bins).fill(0);
  prices.forEach(
    (p) => counts[Math.min(bins - 1, Math.floor((p - min) / step))]++,
  );
  return counts.map((count, i) => ({
    bin: `$${Math.round(min + i * step)}`,
    count,
  }));
}

/** Count room type occurrences. */
function roomTypeCounts(listings: { room_type?: string }[]) {
  const map: Record<string, number> = {};
  listings.forEach((l) => {
    if (l.room_type) map[l.room_type] = (map[l.room_type] ?? 0) + 1;
  });
  return Object.entries(map).map(([name, value]) => ({ name, value }));
}

export default function AnalyticsPage() {
  const [cityId, setCityId] = useState("london");
  const { data: cities } = useCities();
  const { data: listingsData, isLoading } = useListings(cityId, {
    limit: 1000,
  });

  const listings = listingsData?.listings ?? [];
  const prices = useMemo(
    () => listings.map((l) => l.price ?? 0).filter(Boolean),
    [listings],
  );
  const dist = useMemo(() => histogram(prices), [prices]);
  const roomDist = useMemo(() => roomTypeCounts(listings), [listings]);

  // Neighbourhood average prices for bar chart
  const neighbourhoodAvg = useMemo(() => {
    const map: Record<string, { sum: number; count: number }> = {};
    listings.forEach((l) => {
      const n = l.neighbourhood_cleansed ?? "Unknown";
      if (!map[n]) map[n] = { sum: 0, count: 0 };
      map[n].sum += l.price ?? 0;
      map[n].count++;
    });
    return Object.entries(map)
      .map(([name, { sum, count }]) => ({
        name,
        avg_price: Math.round(sum / count),
      }))
      .sort((a, b) => b.avg_price - a.avg_price)
      .slice(0, 10);
  }, [listings]);

  const cachedCities =
    cities?.filter((c) => c.is_cached).map((c) => c.city_id) ?? [];

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Analytics"
        subtitle="Explore price distributions and listing patterns"
        action={
          <select
            className="input w-40 text-sm"
            value={cityId}
            onChange={(e) => setCityId(e.target.value)}
          >
            {AVAILABLE_CITIES.map((id) => {
              const city = cities?.find((c) => c.city_id === id);
              return (
                <option key={id} value={id} disabled={!cachedCities.includes(id)}>
                  {city?.name ?? id}
                  {!cachedCities.includes(id) ? " (not cached)" : ""}
                </option>
              );
            })}
          </select>
        }
      />

      {isLoading ? (
        <FullPageSpinner message="Loading listings data…" />
      ) : listings.length === 0 ? (
        <EmptyState
          title="No data for this city"
          description="Go to the Cities page and fetch data first."
        />
      ) : (
        <div className="space-y-4">
          {/* Summary row */}
          <div className="grid grid-cols-3 gap-4">
            {[
              {
                label: "Total Listings",
                value: listings.length.toLocaleString(),
              },
              {
                label: "Avg Price",
                value: prices.length
                  ? `$${(prices.reduce((a, b) => a + b, 0) / prices.length).toFixed(0)}`
                  : "—",
              },
              {
                label: "Median Price",
                value: prices.length
                  ? `$${prices
                      .slice()
                      .sort((a, b) => a - b)
                      [Math.floor(prices.length / 2)].toFixed(0)}`
                  : "—",
              },
            ].map(({ label, value }) => (
              <div key={label} className="card p-4">
                <p className="text-xs text-slate-500 uppercase tracking-wider">
                  {label}
                </p>
                <p className="text-2xl font-bold text-slate-100 mt-1">
                  {value}
                </p>
              </div>
            ))}
          </div>

          {/* Charts grid */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="card p-5">
              <h3 className="text-sm font-semibold text-slate-300 mb-4">
                Price Distribution
              </h3>
              <PriceDistributionChart data={dist} height={220} />
            </div>

            <div className="card p-5">
              <h3 className="text-sm font-semibold text-slate-300 mb-4">
                Room Types
              </h3>
              <RoomTypePieChart data={roomDist} height={220} />
            </div>
          </div>

          {neighbourhoodAvg.length > 0 && (
            <div className="card p-5">
              <h3 className="text-sm font-semibold text-slate-300 mb-4">
                Avg Price by Neighbourhood (Top 10)
              </h3>
              <ComparisonBarChart
                data={neighbourhoodAvg}
                keys={[{ key: "avg_price", label: "Avg Price ($)" }]}
                height={240}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
