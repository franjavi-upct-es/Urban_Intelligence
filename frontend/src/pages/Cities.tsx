// frontend/src/pages/Cities.tsx
// Urban Intelligence Framework - Cities Management Page

import { useState } from "react";
import { Map, Search, Download, RefreshCw, ExternalLink } from "lucide-react";
import {
  Card,
  CardHeader,
  CardContent,
  CardTitle,
  Button,
  Input,
  Badge,
  EmptyState,
  Spinner,
} from "@/components/ui";
import { useCities, useFetchCity, useCityStatistics } from "@/hooks";
import { City } from "@/types";
import { formatCurrency, formatNumber, formatRelativeTime, cn } from "@/utils";

export function Cities() {
  const [search, setSearch] = useState("");
  const [selectedCity, setSelectedCity] = useState<string | null>(null);
  const { data: cities, isLoading } = useCities();
  const fetchCity = useFetchCity();
  const { data: stats } = useCityStatistics(selectedCity || "");

  const filteredCities = cities?.filter(
    (city) =>
      city.display_name.toLowerCase().includes(search.toLowerCase()) ||
      city.country.toLowerCase().includes(search.toLowerCase()),
  );

  const handleFetch = (cityId: string) => {
    fetchCity.mutate({ cityId, force: false });
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Cities
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            Manage city data and view statistics
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <Input
              placeholder="Search cities..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 w-64"
            />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Cities List */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Map className="w-5 h-5 text-primary-600" />
                Available Cities
                {cities && (
                  <Badge variant="info" className="ml-2">
                    {cities.length} cities
                  </Badge>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="flex justify-center py-8">
                  <Spinner className="w-8 h-8" />
                </div>
              ) : !filteredCities?.length ? (
                <EmptyState
                  icon={<Map className="w-8 h-8 text-gray-400" />}
                  title="No cities found"
                  description={
                    search
                      ? "Try a different search term"
                      : "No cities available"
                  }
                />
              ) : (
                <div className="divide-y divide-gray-200 dark:divide-gray-700">
                  {filteredCities.map((city) => (
                    <CityRow
                      key={city.city_id}
                      city={city}
                      isSelected={selectedCity === city.city_id}
                      onSelect={() => setSelectedCity(city.city_id)}
                      onFetch={() => handleFetch(city.city_id)}
                      isFetching={
                        fetchCity.isPending &&
                        fetchCity.variables?.cityId === city.city_id
                      }
                    />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* City Details Sidebar */}
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>City Details</CardTitle>
            </CardHeader>
            <CardContent>
              {selectedCity && stats ? (
                <div className="space-y-4">
                  <div>
                    <p className="text-sm text-gray-500">Total Listings</p>
                    <p className="text-2xl font-bold">
                      {formatNumber(stats.listings_count, 0)}
                    </p>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm text-gray-500">Avg Price</p>
                      <p className="text-lg font-semibold">
                        {formatCurrency(stats.price_mean)}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">Median Price</p>
                      <p className="text-lg font-semibold">
                        {formatCurrency(stats.price_median)}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">Min Price</p>
                      <p className="text-lg font-semibold">
                        {formatCurrency(stats.price_min)}
                      </p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-500">Max Price</p>
                      <p className="text-lg font-semibold">
                        {formatCurrency(stats.price_max)}
                      </p>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500">
                  <p>Select a city to view details</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Data Sources */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Data Sources</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <DataSourceItem
                name="Inside Airbnb"
                status="connected"
                url="http://insideairbnb.com"
              />
              <DataSourceItem
                name="Open-Meteo"
                status="connected"
                url="https://open-meteo.com"
              />
              <DataSourceItem
                name="OpenStreetMap"
                status="connected"
                url="https://www.openstreetmap.org"
              />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

// City Row Component
function CityRow({
  city,
  isSelected,
  onSelect,
  onFetch,
  isFetching,
}: {
  city: City;
  isSelected: boolean;
  onSelect: () => void;
  onFetch: () => void;
  isFetching: boolean;
}) {
  return (
    <div
      onClick={onSelect}
      className={cn(
        "flex items-center justify-between py-4 px-2 -mx-2 rounded-lg cursor-pointer transition-colors",
        isSelected
          ? "bg-primary-50 dark:bg-primary-900/20"
          : "hover:bg-gray-50 dark:hover:bg-gray-700/50",
      )}
    >
      <div className="flex items-center gap-4">
        <div className="w-10 h-10 bg-gray-100 dark:bg-gray-700 rounded-full flex items-center justify-center">
          <span className="text-sm font-medium">
            {city.display_name.slice(0, 2).toUpperCase()}
          </span>
        </div>
        <div>
          <p className="font-medium text-gray-900 dark:text-white">
            {city.display_name}
          </p>
          <p className="text-sm text-gray-500">{city.country}</p>
        </div>
      </div>
      <div className="flex items-center gap-4">
        <div className="text-right">
          <p className="text-sm font-medium">
            {formatNumber(city.listing_count, 0)} listings
          </p>
          <p className="text-xs text-gray-500">
            {city.last_updated
              ? formatRelativeTime(city.last_updated)
              : "Not fetched"}
          </p>
        </div>
        <Badge
          variant={
            city.airbnb_status === "cached"
              ? "success"
              : city.airbnb_status === "downloading"
                ? "info"
                : "default"
          }
        >
          {city.airbnb_status}
        </Badge>
        <Button
          size="sm"
          variant="outline"
          onClick={(e) => {
            e.stopPropagation();
            onFetch();
          }}
          disabled={isFetching}
        >
          {isFetching ? (
            <RefreshCw className="w-4 h-4 animate-spin" />
          ) : (
            <Download className="w-4 h-4" />
          )}
        </Button>
      </div>
    </div>
  );
}

// Data Source Item
function DataSourceItem({
  name,
  status,
  url,
}: {
  name: string;
  status: string;
  url: string;
}) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        <div
          className={cn(
            "w-2 h-2 rounded-full",
            status === "connected" ? "bg-green-500" : "bg-gray-400",
          )}
        />
        <span className="text-sm text-gray-700 dark:text-gray-300">{name}</span>
      </div>
      <a
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        className="text-gray-400 hover:text-primary-600"
      >
        <ExternalLink className="w-4 h-4" />
      </a>
    </div>
  );
}

export default Cities;
