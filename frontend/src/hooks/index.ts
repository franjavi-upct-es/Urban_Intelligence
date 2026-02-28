// frontend/src/hooks/index.ts
// Urban Intelligence Framework - Custom React Hooks

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, useEffect, useCallback } from "react";
import {
  citiesApi,
  predictionsApi,
  modelApi,
  monitoringApi,
  healthApi,
  experimentsApi,
  realtimeService,
} from "@/services/api";
import { PredictionRequest, PerformanceMetrics } from "@/types";
import { getStoredValue, setStoredValue } from "@/utils";

// =============================================================================
// Health Hook
// =============================================================================

export function useHealth() {
  return useQuery({
    queryKey: ["health"],
    queryFn: healthApi.check,
    refetchInterval: 30000, // 30 seconds
  });
}

// =============================================================================
// Cities Hook
// =============================================================================

export function useCities(cachedOnly = false) {
  return useQuery({
    queryKey: ["cities", cachedOnly],
    queryFn: () => citiesApi.list(cachedOnly),
  });
}

export function useCity(cityId: string) {
  return useQuery({
    queryKey: ["city", cityId],
    queryFn: () => citiesApi.get(cityId),
    enabled: !!cityId,
  });
}

export function useCityStatistics(cityId: string) {
  return useQuery({
    queryKey: ["cityStatistics", cityId],
    queryFn: () => citiesApi.getStatistics(cityId),
    enabled: !!cityId,
  });
}

export function useFetchCity() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ cityId, force }: { cityId: string; force?: boolean }) =>
      citiesApi.fetch(cityId, force),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cities"] });
    },
  });
}

// =============================================================================
// Prediction Hooks
// =============================================================================

export function usePrediction() {
  return useMutation({
    mutationFn: (request: PredictionRequest) => predictionsApi.predict(request),
  });
}

export function useBatchPrediction() {
  return useMutation({
    mutationFn: (requests: PredictionRequest[]) =>
      predictionsApi.predictBatch(requests),
  });
}
// =============================================================================
// Model Hooks
// =============================================================================

export function useModelInfo() {
  return useQuery({
    queryKey: ["model-info"],
    queryFn: modelApi.getInfo,
  });
}

export function useFeatureImportance() {
  return useQuery({
    queryKey: ["feature-importance"],
    queryFn: modelApi.getFeatureImportance,
  });
}

// =============================================================================
// Monitoring Hooks
// =============================================================================

export function usePerformanceMetrics() {
  return useQuery({
    queryKey: ["performance"],
    queryFn: monitoringApi.getPerformance,
    refetchInterval: 60000, // 1 minute
  });
}

export function useDriftReport() {
  return useQuery({
    queryKey: ["drift"],
    queryFn: monitoringApi.getDriftReport,
    refetchInterval: 300000, // 5 minutes
  });
}

// =============================================================================
// Experiments Hooks (A/B Testing)
// =============================================================================

export function useExperiments() {
  return useQuery({
    queryKey: ["experiments"],
    queryFn: experimentsApi.list,
  });
}

export function useExperiment(experimentId: string) {
  return useQuery({
    queryKey: ["experiment", experimentId],
    queryFn: () => experimentsApi.get(experimentId),
    enabled: !!experimentId,
  });
}

export function useCreateExperiment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: experimentsApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["experiments"] });
    },
  });
}

export function useStartExperiment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: experimentsApi.start,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["experiments"] });
    },
  });
}

export function useStopExperiment() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: experimentsApi.stop,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["experiments"] });
    },
  });
}

// =============================================================================
// Real-time Hooks
// =============================================================================

export function useRealtimeMetrics() {
  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null);

  useEffect(() => {
    realtimeService.connect();

    const unsubscribe = realtimeService.subscribe<PerformanceMetrics>(
      "metrics_update",
      (data) => setMetrics(data),
    );

    return () => {
      unsubscribe();
    };
  }, []);

  return metrics;
}

export function useRealtimePredictions() {
  const [predictions, setPredictions] = useState<number[]>([]);

  useEffect(() => {
    realtimeService.connect();

    const unsubscribe = realtimeService.subscribe<{ price: number }>(
      "prediction",
      (data) => {
        setPredictions((prev) => [...prev.slice(-99), data.price]);
      },
    );

    return () => {
      unsubscribe();
    };
  }, []);

  return predictions;
}

// =============================================================================
// Local Storage Hooks
// =============================================================================

export function useLocalStorage<T>(key: string, defaultValue: T) {
  const [value, setValue] = useState<T>(() =>
    getStoredValue(key, defaultValue),
  );

  const setStoredValueCallback = useCallback(
    (newValue: T | ((prev: T) => T)) => {
      setValue((prev) => {
        const result =
          typeof newValue === "function"
            ? (newValue as (prev: T) => T)(prev)
            : newValue;
        setStoredValue(key, result);
        return result;
      });
    },
    [key],
  );

  return [value, setStoredValueCallback] as const;
}

// =============================================================================
// Theme Hook
// =============================================================================

export function useTheme() {
  const [theme, setTheme] = useLocalStorage<"light" | "dark">("theme", "light");

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setTheme((prev) => (prev === "light" ? "dark" : "light"));
  }, [setTheme]);

  return { theme, setTheme, toggleTheme };
}

// =============================================================================
// Media Query Hook
// =============================================================================

export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(false);

  useEffect(() => {
    const media = window.matchMedia(query);
    setMatches(media.matches);

    const listener = (e: MediaQueryListEvent) => setMatches(e.matches);
    media.addEventListener("change", listener);

    return () => media.removeEventListener("change", listener);
  }, [query]);

  return matches;
}

export function useIsMobile(): boolean {
  return useMediaQuery("(max-width: 768px)");
}
