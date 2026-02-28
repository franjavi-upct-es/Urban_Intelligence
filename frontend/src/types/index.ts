// frontend/src/types/index.ts
// Urban Intelligence Framework - TypeScript Type Definitions

// =============================================================================
// API Response Types
// =============================================================================

export interface City {
  city_id: string;
  display_name: string;
  country: string;
  listing_count: number;
  airbnb_status: DataStatus;
  weather_status: DataStatus;
  poi_status: DataStatus;
  last_updated: string | null;
}

export type DataStatus =
  | "available"
  | "downloading"
  | "cached"
  | "error"
  | "unknown";

export interface CityStatistics {
  city_id: string;
  listings_count: number;
  price_mean: number;
  price_median: number;
  price_std: number;
  price_min: number;
  price_max: number;
}

export interface PredictionRequest {
  accommodates: number;
  bedrooms: number;
  beds: number;
  bathrooms: number;
  latitude: number;
  longitude: number;
  room_type: RoomType;
  property_type?: string;
  minimum_nights?: number;
  availability_365?: number;
  number_of_reviews?: number;
  review_scores_rating?: number;
  instant_bookable?: boolean;
  host_is_superhost?: boolean;
}

export interface PredictionResponse {
  predicted_price: number;
  confidence_interval: [number, number];
  currency: string;
  model_version: string;
  prediction_timestamp: string;
  features_used: Record<string, unknown>;
}

export type RoomType =
  | "Entire home/apt"
  | "Private room"
  | "Shared room"
  | "Hotel room";

// =============================================================================
// Model & Monitoring Types
// =============================================================================

export interface ModelInfo {
  model_type: string;
  version: string;
  trained_at: string | null;
  metrics: Record<string, number>;
  feature_importance: Record<string, number>;
}

export interface PerformanceMetrics {
  mae: number;
  rmse: number;
  r2: number;
  mape: number;
  latency_mean_ms: number;
  latency_p95_ms: number;
  prediction_count: number;
  error_rate: number;
}

export interface DriftReport {
  report_time: string;
  total_features: number;
  features_with_drift: number;
  drift_percentage: number;
  overall_severity: DriftSeverity;
  recommendations: string[];
}

export type DriftSeverity = "none" | "low" | "medium" | "high" | "critical";

export interface Alert {
  alert_id: string;
  timestamp: string;
  level: AlertLevel;
  metric_name: string;
  current_value: number;
  threshold_value: number;
  message: string;
}

export type AlertLevel = "info" | "warning" | "error" | "critical";

// =============================================================================
// Health & Status Types
// =============================================================================

export interface HealthStatus {
  status: "healthy" | "degraded" | "unhealthy";
  version: string;
  model_loaded: boolean;
  database_connected: boolean;
  timestamp: string;
}

// =============================================================================
// A/B Testing Types
// =============================================================================

export interface Experiment {
  id: string;
  name: string;
  description: string;
  status: ExperimentStatus;
  variantes: Variant[];
  metrics: ExperimentMetrics;
  created_at: string;
  started_at: string | null;
  ended_at: string | null;
}

export type ExperimentStatus = "draft" | "running" | "paused" | "completed";

export interface Variant {
  id: string;
  name: string;
  model_version: string;
  traffic_percentage: number;
  predictions_count: number;
  metrics: Record<string, number>;
}

export interface ExperimentMetrics {
  total_predictions: number;
  winner: string | null;
  confidence: number;
  lift: number;
}

// =============================================================================
// Chart Data Types
// =============================================================================

export interface TimeSeriesPoint {
  timestamp: string;
  value: number;
}

export interface PriceDistribution {
  range: string;
  count: number;
  percentage: number;
}

export interface FeatureImportance {
  feature: string;
  importance: number;
}

// =============================================================================
// Form Types
// =============================================================================

export interface PredictionFormData {
  accommodates: number;
  bedrooms: number;
  beds: number;
  bathrooms: number;
  latitude: number;
  longitude: number;
  room_type: RoomType;
  property_type: string;
  minimum_nights: number;
  availability_365: number;
  number_of_reviews: number;
  review_scores_rating: number;
  instant_bookable: boolean;
  host_is_superhost: boolean;
}

export const DEFAULT_PREDICTION_FORM: PredictionFormData = {
  accommodates: 4,
  bedrooms: 2,
  beds: 2,
  bathrooms: 1,
  latitude: 40.4168,
  longitude: -3.7038,
  room_type: "Entire home/apt",
  property_type: "Apartment",
  minimum_nights: 2,
  availability_365: 180,
  number_of_reviews: 50,
  review_scores_rating: 4.5,
  instant_bookable: true,
  host_is_superhost: false,
};
