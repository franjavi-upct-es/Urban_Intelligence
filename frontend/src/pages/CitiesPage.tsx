// frontend/src/pages/CitiesPage.tsx
// Urban Intelligence Framework v2.0.0
// Cities page — browse catalogue and trigger data fetches

import { useState } from "react";
import { Download, RefreshCw, MapPin, Globe } from "lucide-react";
import { useCities, useFetchCity, useListings } from "@/hooks";
import {
  SectionHeader,
  FullPageSpinner,
  ErrorBanner,
  Badge,
  Table,
  EmptyState,
} from "@/components/ui";
import type { City } from "@/types";

function CityCard({
  city,
  onFetch,
  isFetching,
}: {
  city: City;
  onFetch: (cityId: string) => void;
  isFetching: boolean;
}) {
  return (
    <div className="card p-5 flex flex-col gap-3">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="font-semibold text-slate-200">{city.name}</h3>
          <p className="text-xs text-slate-500 flex items-center gap-1 mt-0.5">
            <Globe size={11} /> {city.country}
          </p>
        </div>
        <Badge variant={city.is_cached ? "green" : "gray"}>
          {city.is_cached ? "Cached" : "Not fetched"}
        </Badge>
      </div>

      <div className="text-xs text-slate-600 flex items-center gap-1">
        <MapPin size={11} />
        {city.latitude.toFixed(4)}, {city.longitude.toFixed(4)}
      </div>

      <div className="flex items-center justify-between mt-auto pt-2 border-t border-slate-700/30">
        <span className="text-xs text-slate-600">{city.currency}</span>
        <button
          onClick={() => onFetch(city.city_id)}
          disabled={isFetching}
          className="btn-secondary text-xs flex items-center gap-1.5 px-3 py-1.5"
        >
          {isFetching ? (
            <RefreshCw size={12} className="animate-spin" />
          ) : (
            <Download size={12} />
          )}
          {city.is_cached ? "Refresh" : "Fetch"}
        </button>
      </div>
    </div>
  );
}

function ListingsPanel({ cityId }: { cityId: string }) {
  const { data, isLoading } = useListings(cityId, { limit: 20 });

  if (isLoading)
    return <div className="text-sm text-slate-500 py-4">Loading listings…</div>;
  if (!data?.listings.length)
    return (
      <EmptyState
        title="No listings cached"
        description="Fetch city data first"
      />
    );

  const rows = data.listings.map((l) => [
    l.id,
    l.room_type ?? "—",
    l.neighbourhood_cleansed ?? "—",
    l.bedrooms != null ? `${l.bedrooms}br` : "—",
    l.price != null ? `$${l.price.toFixed(2)}` : "—",
    l.review_scores_rating != null ? l.review_scores_rating.toFixed(1) : "—",
  ]);

  return (
    <div className="mt-4">
      <p className="text-xs text-slate-500 mb-2">
        Showing {data.listings.length} of {data.total} listings
      </p>
      <Table
        headers={[
          "ID",
          "Room Type",
          "Neighbourhood",
          "Beds",
          "Price",
          "Rating",
        ]}
        rows={rows}
      />
    </div>
  );
}

export default function CitiesPage() {
  const { data: cities, isLoading, error } = useCities();
  const fetchCity = useFetchCity();
  const [selectedCity, setSelectedCity] = useState<string | null>(null);
  const [fetchingId, setFetchingId] = useState<string | null>(null);

  function handleFetch(cityId: string) {
    setFetchingId(cityId);
    fetchCity.mutate({ cityId }, { onSettled: () => setFetchingId(null) });
  }

  if (isLoading) return <FullPageSpinner message="Loading cities…" />;
  if (error) return <ErrorBanner message="Failed to load cities." />;

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Cities"
        subtitle={`${cities?.length ?? 0} cities in the Inside Airbnb catalogue`}
      />

      {/* ── City grid ──────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {(cities ?? []).map((city) => (
          <div
            key={city.city_id}
            onClick={() =>
              setSelectedCity(
                city.city_id === selectedCity ? null : city.city_id,
              )
            }
            className={`cursor-pointer transition-all duration-150 ${selectedCity === city.city_id ? "ring-2 ring-brand-500 rounded-xl" : ""}`}
          >
            <CityCard
              city={city}
              onFetch={(id) => {
                handleFetch(id);
              }}
              isFetching={fetchingId === city.city_id}
            />
          </div>
        ))}
      </div>

      {/* ── Listings preview ────────────────────────────────────────────── */}
      {selectedCity && (
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-slate-300 mb-1">
            Listings preview —{" "}
            {cities?.find((c) => c.city_id === selectedCity)?.name}
          </h3>
          <ListingsPanel cityId={selectedCity} />
        </div>
      )}
    </div>
  );
}
