// frontend/src/api/services.ts
// Urban Intelligence Framework v2.0.0
// Typed API service functions for all backend endpoints

import { apiClient } from "./client";
import type {
  City,
  PredictionRequest,
  PredictionResponse,
  BatchPredictionRequest,
  MonitoringSnapshot,
  Experiment,
  CreateExperimentRequest,
  ExperimentResult,
  ListingsResponse,
} from "@/types";

// ── Cities ────────────────────────────────────────────────────────────────

export const citiesApi = {
  list: () => apiClient.get<City[]>("/cities/").then((r) => r.data),

  get: (cityId: string) =>
    apiClient.get<City>(`/cities/${cityId}`).then((r) => r.data),

  fetch: (cityId: string, forceRefresh = false) =>
    apiClient
      .post<{ message: string; city_id: string }>(`/cities/${cityId}/fetch`, {
        force_refresh: forceRefresh,
      })
      .then((r) => r.data),

  listings: (
    cityId: string,
    params?: { limit?: number; room_type?: string; neighbourhood?: string },
  ) =>
    apiClient
      .get<ListingsResponse>(`/cities/${cityId}/listings`, { params })
      .then((r) => r.data),
};

// ── Predictions ───────────────────────────────────────────────────────────

export const predictionsApi = {
  single: (features: PredictionRequest) =>
    apiClient
      .post<PredictionResponse>("/predictions/single", features)
      .then((r) => r.data),

  batch: (request: BatchPredictionRequest) =>
    apiClient
      .post<{
        count: number;
        predictions: PredictionResponse[];
      }>("/predictions/batch", request)
      .then((r) => r.data),

  history: (limit = 50) =>
    apiClient
      .get<{ total: number; history: PredictionResponse[] }>(
        "/predictions/history",
        {
          params: { limit },
        },
      )
      .then((r) => r.data),
};

// ── Monitoring ────────────────────────────────────────────────────────────

export const monitoringApi = {
  snapshot: (cityId: string) =>
    apiClient
      .get<MonitoringSnapshot>(`/monitoring/snapshot/${cityId}`)
      .then((r) => r.data),

  allAlerts: () =>
    apiClient
      .get<{
        total: number;
        alerts: MonitoringSnapshot["active_alerts"];
      }>("/monitoring/alerts")
      .then((r) => r.data),

  resolveAlert: (alertId: string) =>
    apiClient
      .post<{ message: string }>(`/monitoring/alerts/${alertId}/resolve`)
      .then((r) => r.data),

  monitoredCities: () =>
    apiClient
      .get<{
        cities: Array<{
          city_id: string;
          n_predictions: number;
          active_alerts: number;
        }>;
      }>("/monitoring/cities")
      .then((r) => r.data),
};

// ── Experiments ───────────────────────────────────────────────────────────

export const experimentsApi = {
  list: () =>
    apiClient
      .get<{ experiments: Experiment[] }>("/experiments/")
      .then((r) => r.data),

  create: (request: CreateExperimentRequest) =>
    apiClient
      .post<{
        experiment_id: string;
        name: string;
        status: string;
      }>("/experiments/", request)
      .then((r) => r.data),

  get: (experimentId: string) =>
    apiClient
      .get<Experiment>(`/experiments/${experimentId}`)
      .then((r) => r.data),

  start: (experimentId: string) =>
    apiClient
      .post<{ message: string }>(`/experiments/${experimentId}/start`)
      .then((r) => r.data),

  pause: (experimentId: string) =>
    apiClient
      .post<{ message: string }>(`/experiments/${experimentId}/pause`)
      .then((r) => r.data),

  complete: (experimentId: string) =>
    apiClient
      .post<ExperimentResult>(`/experiments/${experimentId}/complete`)
      .then((r) => r.data),

  results: (experimentId: string) =>
    apiClient
      .get<ExperimentResult>(`/experiments/${experimentId}/results`)
      .then((r) => r.data),
};
