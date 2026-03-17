// frontend/src/pages/PredictPage.tsx
// Urban Intelligence Framework v2.0.0
// Single listing price prediction form with real-time results

import { useState } from "react";
import { TrendingUp, Zap, Info } from "lucide-react";
import { usePredictSingle, useCities } from "@/hooks";
import {
  SectionHeader,
  ErrorBanner,
  Badge,
  ProgressBar,
} from "@/components/ui";
import type { PredictionRequest, PredictionResponse } from "@/types";

const ROOM_TYPES = [
  "Entire home/apt",
  "Private room",
  "Shared room",
  "Hotel room",
];
const PROPERTY_TYPES = [
  "Apartment",
  "House",
  "Condo",
  "Loft",
  "Studio",
  "Villa",
  "Townhouse",
];

const DEFAULT_FORM: PredictionRequest = {
  city_id: "london",
  room_type: "Entire home/apt",
  property_type: "Apartment",
  neighbourhood: "Westminster",
  accommodates: 2,
  bedrooms: 1,
  beds: 1,
  bathrooms: 1,
  amenity_count: 15,
  review_scores_rating: 4.5,
  number_of_reviews: 30,
  availability_365: 200,
  minimum_nights: 2,
  host_is_superhost: false,
  instant_bookable: false,
  latitude: 51.5074,
  longitude: -0.1278,
};

function ResultCard({ result }: { result: PredictionResponse }) {
  const range =
    result.confidence_interval.upper - result.confidence_interval.lower;
  const fill = Math.min(
    100,
    ((result.predicted_price - result.confidence_interval.lower) / range) * 100,
  );

  return (
    <div className="card p-6 space-y-5 animate-slide-up">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-slate-200">Prediction Result</h3>
        <Badge variant="blue">v{result.model_version}</Badge>
      </div>

      {/* Main price */}
      <div className="text-center py-4">
        <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">
          Predicted nightly price
        </p>
        <p className="text-5xl font-bold text-brand-400">
          ${result.predicted_price.toFixed(2)}
        </p>
        <p className="text-sm text-slate-500 mt-1">{result.currency}</p>
      </div>

      {/* Confidence interval */}
      <div>
        <div className="flex justify-between text-xs text-slate-500 mb-1">
          <span>${result.confidence_interval.lower.toFixed(0)}</span>
          <span className="text-slate-400">80% confidence interval</span>
          <span>${result.confidence_interval.upper.toFixed(0)}</span>
        </div>
        <ProgressBar value={fill} color="brand" />
      </div>

      {/* Meta */}
      <div className="grid grid-cols-2 gap-3 pt-2 border-t border-slate-700/50">
        <div>
          <p className="text-xs text-slate-600">City</p>
          <p className="text-sm font-medium text-slate-300 capitalize">
            {result.city_id}
          </p>
        </div>
        <div>
          <p className="text-xs text-slate-600">Latency</p>
          <p className="text-sm font-medium text-slate-300">
            {result.latency_ms.toFixed(1)} ms
          </p>
        </div>
      </div>
    </div>
  );
}

export default function PredictPage() {
  const [form, setForm] = useState<PredictionRequest>(DEFAULT_FORM);
  const { data: cities } = useCities();
  const predict = usePredictSingle();

  function set<K extends keyof PredictionRequest>(
    key: K,
    value: PredictionRequest[K],
  ) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    predict.mutate(form);
  }

  return (
    <div className="space-y-6">
      <SectionHeader
        title="Price Predictor"
        subtitle="Enter listing attributes to get an AI-powered price estimate"
      />

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* ── Input form ─────────────────────────────────────────────────── */}
        <form onSubmit={handleSubmit} className="card p-6 space-y-5">
          <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Listing Details
          </p>

          {/* City + room type */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-500 mb-1">City</label>
              <select
                className="input"
                value={form.city_id}
                onChange={(e) => set("city_id", e.target.value)}
              >
                {(cities ?? []).map((c) => (
                  <option key={c.city_id} value={c.city_id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">
                Room Type
              </label>
              <select
                className="input"
                value={form.room_type}
                onChange={(e) => set("room_type", e.target.value)}
              >
                {ROOM_TYPES.map((rt) => (
                  <option key={rt}>{rt}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Property type + neighbourhood */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-500 mb-1">
                Property Type
              </label>
              <select
                className="input"
                value={form.property_type}
                onChange={(e) => set("property_type", e.target.value)}
              >
                {PROPERTY_TYPES.map((pt) => (
                  <option key={pt}>{pt}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">
                Neighbourhood
              </label>
              <input
                className="input"
                value={form.neighbourhood}
                onChange={(e) => set("neighbourhood", e.target.value)}
              />
            </div>
          </div>

          {/* Capacity */}
          <div className="grid grid-cols-4 gap-3">
            {(["accommodates", "bedrooms", "beds", "bathrooms"] as const).map(
              (field) => (
                <div key={field}>
                  <label className="block text-xs text-slate-500 mb-1 capitalize">
                    {field}
                  </label>
                  <input
                    type="number"
                    min={0}
                    max={20}
                    step={field === "bathrooms" ? 0.5 : 1}
                    className="input"
                    value={form[field]}
                    onChange={(e) => set(field, parseFloat(e.target.value))}
                  />
                </div>
              ),
            )}
          </div>

          {/* Quality signals */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-500 mb-1">
                Review Score (0–5)
              </label>
              <input
                type="number"
                min={0}
                max={5}
                step={0.1}
                className="input"
                value={form.review_scores_rating}
                onChange={(e) =>
                  set("review_scores_rating", parseFloat(e.target.value))
                }
              />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">
                Amenity Count
              </label>
              <input
                type="number"
                min={0}
                max={100}
                className="input"
                value={form.amenity_count}
                onChange={(e) => set("amenity_count", parseInt(e.target.value))}
              />
            </div>
          </div>

          {/* Availability */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-500 mb-1">
                Availability (days/year)
              </label>
              <input
                type="number"
                min={0}
                max={365}
                className="input"
                value={form.availability_365}
                onChange={(e) =>
                  set("availability_365", parseInt(e.target.value))
                }
              />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">
                Min Nights
              </label>
              <input
                type="number"
                min={1}
                max={365}
                className="input"
                value={form.minimum_nights}
                onChange={(e) =>
                  set("minimum_nights", parseInt(e.target.value))
                }
              />
            </div>
          </div>

          {/* Boolean toggles */}
          <div className="flex gap-6">
            {(["host_is_superhost", "instant_bookable"] as const).map(
              (field) => (
                <label
                  key={field}
                  className="flex items-center gap-2 cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={!!form[field]}
                    onChange={(e) => set(field, e.target.checked)}
                    className="w-4 h-4 rounded border-slate-600 bg-surface-900 text-brand-500 focus:ring-brand-500"
                  />
                  <span className="text-sm text-slate-400 capitalize">
                    {field.replace(/_/g, " ")}
                  </span>
                </label>
              ),
            )}
          </div>

          {predict.isError && (
            <ErrorBanner message={(predict.error as Error).message} />
          )}

          <button
            type="submit"
            className="btn-primary w-full flex items-center justify-center gap-2"
            disabled={predict.isPending}
          >
            {predict.isPending ? (
              <>
                <span className="animate-spin">⟳</span> Predicting…
              </>
            ) : (
              <>
                <Zap size={16} /> Predict Price
              </>
            )}
          </button>
        </form>

        {/* ── Result panel ───────────────────────────────────────────────── */}
        <div>
          {predict.data ? (
            <ResultCard result={predict.data} />
          ) : (
            <div className="card p-6 h-full flex flex-col items-center justify-center gap-4 text-center">
              <TrendingUp size={48} className="text-slate-700" />
              <div>
                <p className="font-medium text-slate-400">No prediction yet</p>
                <p className="text-sm text-slate-600 mt-1">
                  Fill in the form and click{" "}
                  <strong className="text-slate-400">Predict Price</strong>
                </p>
              </div>
              <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-brand-900/30 border border-brand-700/30 text-xs text-brand-400">
                <Info size={13} />
                Model falls back to rule-based estimation if no trained model is
                available
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
