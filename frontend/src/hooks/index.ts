// frontend/src/hooks/index.ts
// Urban Intelligence Framework v2.0.0
// Custom React Query hooks for all API endpoints

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  citiesApi,
  predictionsApi,
  monitoringApi,
  experimentsApi,
} from "@/api/services";
import type { PredictionRequest, CreateExperimentRequest } from "@/types";

// ── Cities ────────────────────────────────────────────────────────────────

export function useCities() {
  return useQuery({
    queryKey: ["cities"],
    queryFn: citiesApi.list,
    staleTime: 60_000,
  });
}

export function useCity(cityId: string) {
  return useQuery({
    queryKey: ["city", cityId],
    queryFn: () => citiesApi.get(cityId),
    enabled: !!cityId,
  });
}

export function useListings(
  cityId: string,
  params?: { limit?: number; room_type?: string },
) {
  return useQuery({
    queryKey: ["listings", cityId, params],
    queryFn: () => citiesApi.listings(cityId, params),
    enabled: !!cityId,
  });
}

export function useFetchCity() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      cityId,
      forceRefresh,
    }: {
      cityId: string;
      forceRefresh?: boolean;
    }) => citiesApi.fetch(cityId, forceRefresh),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["cities"] }),
  });
}

// ── Predictions ───────────────────────────────────────────────────────────

export function usePredictSingle() {
  return useMutation({
    mutationFn: (features: PredictionRequest) =>
      predictionsApi.single(features),
  });
}

export function usePredictionHistory(limit = 50) {
  return useQuery({
    queryKey: ["prediction-history", limit],
    queryFn: () => predictionsApi.history(limit),
    refetchInterval: 30_000,
  });
}

// ── Monitoring ────────────────────────────────────────────────────────────

export function useMonitoringSnapshot(cityId: string, enabled = true) {
  return useQuery({
    queryKey: ["monitoring", cityId],
    queryFn: () => monitoringApi.snapshot(cityId),
    enabled: !!cityId && enabled,
    refetchInterval: 10_000,
  });
}

export function useAllAlerts() {
  return useQuery({
    queryKey: ["alerts"],
    queryFn: monitoringApi.allAlerts,
    refetchInterval: 15_000,
  });
}

export function useResolveAlert() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (alertId: string) => monitoringApi.resolveAlert(alertId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["alerts"] });
      qc.invalidateQueries({ queryKey: ["monitoring"] });
    },
  });
}

export function useMonitoredCities() {
  return useQuery({
    queryKey: ["monitored-cities"],
    queryFn: monitoringApi.monitoredCities,
  });
}

// ── Experiments ───────────────────────────────────────────────────────────

export function useExperiments() {
  return useQuery({
    queryKey: ["experiments"],
    queryFn: () => experimentsApi.list(),
  });
}

export function useExperiment(id: string) {
  return useQuery({
    queryKey: ["experiment", id],
    queryFn: () => experimentsApi.get(id),
    enabled: !!id,
  });
}

export function useCreateExperiment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (req: CreateExperimentRequest) => experimentsApi.create(req),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["experiments"] }),
  });
}

export function useStartExperiment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => experimentsApi.start(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["experiments"] }),
  });
}

export function useCompleteExperiment() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => experimentsApi.complete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["experiments"] }),
  });
}
