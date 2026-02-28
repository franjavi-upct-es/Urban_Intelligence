// frontend/src/pages/Analytics.tsx
// Urban Intelligence Framework - Analytics Dashboard

import { useState } from "react";
import {
  BarChart3,
  TrendingUp,
  MapPin,
  Calendar,
  Download,
} from "lucide-react";
import {
  Card,
  CardHeader,
  CardContent,
  CardTitle,
  Button,
  Select,
} from "@/components/ui";
import {
  SimpleBarChart,
  SimpleAreaChart,
  SimplePieChart,
  FeatureImportanceChart,
} from "@/components/charts";
import { useCityStatistics, useFeatureImportance, useCities } from "@/hooks";
import { formatCurrency, formatNumber } from "@/utils";

export function Analytics() {
  const [selectedCity, setSelectedCity] = useState("madrid");
  const [timeRange, setTimeRange] = useState("30d");

  const { data: cities } = useCities();
  const { data: stats } = useCityStatistics(selectedCity);
  const { data: featureImportance } = useFeatureImportance();

  // Mock data for analytics
  const priceByNeighborhood = [
    { name: "Centro", price: 120 },
    { name: "Salamanca", price: 145 },
    { name: "Chamberí", price: 110 },
    { name: "Retiro", price: 130 },
    { name: "Chamartín", price: 125 },
    { name: "Arganzuela", price: 85 },
    { name: "Moncloa", price: 95 },
    { name: "Latina", price: 75 },
  ];

  const priceByRoomType = [
    { name: "Entire home", value: 65 },
    { name: "Private room", value: 28 },
    { name: "Shared room", value: 5 },
    { name: "Hotel room", value: 2 },
  ];

  const priceDistribution = [
    { range: "$0-50", count: 450 },
    { range: "$51-100", count: 1200 },
    { range: "$101-150", count: 1800 },
    { range: "$151-200", count: 1100 },
    { range: "$201-300", count: 600 },
    { range: "$300+", count: 250 },
  ];

  const seasonalTrend = Array.from({ length: 12 }, (_, i) => ({
    month: [
      "Jan",
      "Feb",
      "Mar",
      "Apr",
      "May",
      "Jun",
      "Jul",
      "Aug",
      "Sep",
      "Oct",
      "Nov",
      "Dec",
    ][i],
    price: 100 + Math.sin((i / 12) * Math.PI * 2) * 30 + Math.random() * 10,
  }));

  const cityOptions = cities?.map((c) => ({
    value: c.city_id,
    label: c.display_name,
  })) || [{ value: "madrid", label: "Madrid" }];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Analytics
          </h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            Deep dive into pricing patterns and trends
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Select
            options={cityOptions}
            value={selectedCity}
            onChange={(e) => setSelectedCity(e.target.value)}
          />
          <Select
            options={[
              { value: "7d", label: "Last 7 days" },
              { value: "30d", label: "Last 30 days" },
              { value: "90d", label: "Last 90 days" },
              { value: "1y", label: "Last year" },
            ]}
            value={timeRange}
            onChange={(e) => setTimeRange(e.target.value)}
          />
          <Button variant="outline" size="sm">
            <Download className="w-4 h-4 mr-2" />
            Export
          </Button>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="py-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Total Listings</p>
                <p className="text-2xl font-bold mt-1">
                  {stats ? formatNumber(stats.listings_count, 0) : "-"}
                </p>
              </div>
              <MapPin className="w-8 h-8 text-primary-300" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Average Price</p>
                <p className="text-2xl font-bold mt-1">
                  {stats ? formatCurrency(stats.price_mean) : "-"}
                </p>
              </div>
              <TrendingUp className="w-8 h-8 text-green-300" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Median Price</p>
                <p className="text-2xl font-bold mt-1">
                  {stats ? formatCurrency(stats.price_median) : "-"}
                </p>
              </div>
              <BarChart3 className="w-8 h-8 text-blue-300" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Price Range</p>
                <p className="text-2xl font-bold mt-1">
                  {stats
                    ? `${formatCurrency(stats.price_min)} - ${formatCurrency(stats.price_max)}`
                    : "-"}
                </p>
              </div>
              <Calendar className="w-8 h-8 text-purple-300" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <SimpleBarChart
          data={priceByNeighborhood}
          xKey="name"
          yKey="price"
          title="Average Price by Neighborhood"
          height={350}
        />
        <SimplePieChart
          data={priceByRoomType}
          title="Listings by Room Type"
          height={350}
        />
      </div>

      {/* Charts Row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <SimpleAreaChart
          data={seasonalTrend}
          xKey="month"
          yKey="price"
          title="Seasonal Price Trend"
          height={350}
        />
        <SimpleBarChart
          data={priceDistribution}
          xKey="range"
          yKey="count"
          title="Price Distribution"
          height={350}
        />
      </div>

      {/* Feature Importance */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <FeatureImportanceChart
          data={
            featureImportance || {
              accommodates: 0.18,
              bedrooms: 0.15,
              room_type: 0.14,
              neighbourhood: 0.12,
              bathrooms: 0.1,
              review_scores: 0.08,
              availability: 0.07,
              minimum_nights: 0.06,
              host_is_superhost: 0.05,
              instant_bookable: 0.05,
            }
          }
          title="Model Feature Importance"
          height={400}
          limit={10}
        />

        {/* Insights Card */}
        <Card>
          <CardHeader>
            <CardTitle>Key Insights</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <InsightItem
              icon={<TrendingUp className="w-5 h-5 text-green-500" />}
              title="Salamanca commands premium"
              description="Listings in Salamanca average 30% higher than city-wide average"
            />
            <InsightItem
              icon={<BarChart3 className="w-5 h-5 text-blue-500" />}
              title="Entire homes dominate"
              description="65% of listings are entire homes, driving higher average prices"
            />
            <InsightItem
              icon={<Calendar className="w-5 h-5 text-purple-500" />}
              title="Summer peak season"
              description="July-August sees 25% price increase compared to winter months"
            />
            <InsightItem
              icon={<MapPin className="w-5 h-5 text-orange-500" />}
              title="Location is key"
              description="Neighborhood and coordinates are among top 5 predictive features"
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function InsightItem({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="flex gap-3 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
      <div className="flex-shrink-0 mt-0.5">{icon}</div>
      <div>
        <p className="font-medium text-gray-900 dark:text-white">{title}</p>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          {description}
        </p>
      </div>
    </div>
  );
}

export default Analytics;
