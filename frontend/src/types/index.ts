// frontend/src/types/index.ts
// Urban Intelligence Framework v2.0.0
// Shared TypeScript type definitions

// ── City ──────────────────────────────────────────────────────────────────

export interface City {
  city_id: string;
  name: string;
  country: string;
  latitude: number;
  longitude: number;
  currency: string;
  is_cached: boolean;
  listing_count?: number | null;
}

// ── Listings ──────────────────────────────────────────────────────────────

export interface Listing {
  id: string;
  neighbourhood_cleansed?: string;
  room_type?: string;
  property_type?: string;
  bedrooms?: number;
  beds?: number;
  bathrooms?: number;
  accommodates?: number;
  price?: number;
  review_scores_rating?: number;
  number_of_reviews?: number;
  latitude?: number;
  longitude?: number;
}

export interface ListingsResponse {
  city_id: string;
  total: number;
  listings: Listing[];
}

// ── Predictions ───────────────────────────────────────────────────────────

export interface PredictionRequest {
  city_id: string;
  room_type: string;
  property_type?: string;
  neighbourhood?: string;
  accommodates: number;
  bedrooms: number;
  beds: number;
  bathrooms: number;
  amenity_count: number;
  review_scores_rating: number;
  number_of_reviews: number;
  availability_365: number;
  minimum_nights: number;
  host_is_superhost: boolean;
  instant_bookable: boolean;
  latitude: number;
  longitude: number;
}

export interface PredictionResponse {
  prediction_id: string;
  city_id: string;
  predicted_price: number;
  currency: string;
  confidence_interval: { lower: number; upper: number };
  latency_ms: number;
  model_version: string;
}

export interface BatchPredictionRequest {
  listings: PredictionRequest[];
}

// ── Monitoring ────────────────────────────────────────────────────────────

export interface Alert {
  alert_id: string;
  city_id?: string;
  metric: string;
  current_value: number;
  threshold: number;
  severity: "warning" | "critical";
  message: string;
  created_at: string;
}

export interface MonitoringSnapshot {
  city_id: string;
  timestamp: string;
  rmse: number | null;
  mae: number | null;
  r2: number | null;
  avg_latency_ms: number | null;
  p95_latency_ms: number | null;
  request_rate: number;
  error_rate: number;
  n_predictions: number;
  active_alerts: Alert[];
}

// ── Experiments ───────────────────────────────────────────────────────────

export type ExperimentStatus = "draft" | "running" | "paused" | "completed";

export interface VariantConfig {
  name: string;
  model_id: string;
  traffic_split: number;
}

export interface VariantMetrics {
  n_samples: number;
  rmse: number | null;
  mae: number | null;
  avg_latency_ms: number | null;
}

export interface ExperimentVariant extends VariantConfig {
  n_samples: number;
  rmse: number | null;
  mae: number | null;
}

export interface Experiment {
  id: string;
  name: string;
  status: ExperimentStatus;
  created_at: string;
  started_at: string | null;
  ended_at: string | null;
  variants: ExperimentVariant[];
}

export interface CreateExperimentRequest {
  name: string;
  description?: string;
  variants: VariantConfig[];
}

export interface ExperimentResult {
  experiment_id: string;
  winner: string | null;
  p_value: number;
  is_significant: boolean;
  confidence_level: number;
  test_method: string;
  variant_metrics: Record<string, VariantMetrics>;
}

// ── Chart helpers ─────────────────────────────────────────────────────────

export interface TimeSeriesPoint {
  date: string;
  value: number;
  label?: string;
}

export interface DistributionBin {
  bin: string;
  count: number;
}
