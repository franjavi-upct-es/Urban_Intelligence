// frontend/src/services/api.ts
// Urban Intelligence Framework - API Service
// Handles all communication with the backend

import axios, { AxiosInstance, AxiosError } from "axios";
import {
  City,
  CityStatistics,
  PredictionRequest,
  PredictionResponse,
  ModelInfo,
  HealthStatus,
  PerformanceMetrics,
  DriftReport,
  Experiment,
} from "@/types";

// =============================================================================
// API Client Configuration
// =============================================================================

const API_BASE_URL = import.meta.env.VITE_API_URL || "/api";

const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 30000,
});

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem("auth_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

// Response interceptor
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    console.error("API Error:", error.response?.data || error.message);
    return Promise.reject(error);
  },
);

// =============================================================================
// Health & Status
// =============================================================================

export const healthApi = {
  check: async (): Promise<HealthStatus> => {
    const response = await apiClient.get<HealthStatus>("/health");
    return response.data;
  },
};

// =============================================================================
// Cities
// =============================================================================

export const citiesApi = {
  list: async (cachedOnly = false): Promise<City[]> => {
    const response = await apiClient.get<{ cities: City[] }>("/cities", {
      params: { cached_only: cachedOnly },
    });
    return response.data.cities;
  },

  get: async (cityId: string): Promise<City> => {
    const response = await apiClient.get<City>(`/cities/${cityId}`);
    return response.data;
  },

  getStatistics: async (cityId: string): Promise<CityStatistics> => {
    const response = await apiClient.get<CityStatistics>(
      `/cities/${cityId}/statistics`,
    );
    return response.data;
  },

  fetch: async (
    cityId: string,
    force = false,
  ): Promise<{ message: string }> => {
    const response = await apiClient.post(`/cities/${cityId}/fetch`, null, {
      params: { force },
    });
    return response.data;
  },
};

// =============================================================================
// Predictions
// =============================================================================

export const predictionsApi = {
  predict: async (request: PredictionRequest): Promise<PredictionResponse> => {
    const response = await apiClient.post<PredictionResponse>(
      "/predict",
      request,
    );
    return response.data;
  },

  predictBatch: async (
    requests: PredictionRequest[],
  ): Promise<{
    predictions: PredictionResponse[];
    processing_time_ms: number;
  }> => {
    const response = await apiClient.post("/predict/batch", {
      listings: requests,
    });
    return response.data;
  },
};

// =============================================================================
// Model
// =============================================================================

export const modelApi = {
  getInfo: async (): Promise<ModelInfo> => {
    const response = await apiClient.get<ModelInfo>("/model/info");
    return response.data;
  },

  getFeatureImportance: async (): Promise<Record<string, number>> => {
    const response = await apiClient.get<{
      feature_importance: Record<string, number>;
    }>("/model/features");
    return response.data.feature_importance;
  },
};

// =============================================================================
// Monitoring
// =============================================================================

export const monitoringApi = {
  getPerformance: async (): Promise<PerformanceMetrics> => {
    const response = await apiClient.get<PerformanceMetrics>(
      "/monitoring/performance",
    );
    return response.data;
  },

  getDriftReport: async (): Promise<DriftReport> => {
    const response = await apiClient.get<DriftReport>("/monitoring/drift");
    return response.data;
  },

  getAlerts: async (
    limit = 10,
  ): Promise<{ alerts: Alert[]; total: number }> => {
    const response = await apiClient.get("/monitoring/alerts", {
      params: { limit },
    });
    return response.data;
  },
};

// =============================================================================
// A/B Testing (v1.2.0)
// =============================================================================

export const experimentsApi = {
  list: async (): Promise<Experiment[]> => {
    const response = await apiClient.get<{ experiments: Experiment[] }>(
      "/experiments",
    );
    return response.data.experiments;
  },

  get: async (experimentId: string): Promise<Experiment> => {
    const response = await apiClient.get<Experiment>(
      `/experiments/${experimentId}`,
    );
    return response.data;
  },

  create: async (experiment: Partial<Experiment>): Promise<Experiment> => {
    const response = await apiClient.post<Experiment>(
      "/experiments",
      experiment,
    );
    return response.data;
  },

  start: async (experimentId: string): Promise<Experiment> => {
    const response = await apiClient.post<Experiment>(
      `/experiments/${experimentId}/start`,
    );
    return response.data;
  },

  stop: async (experimentId: string): Promise<Experiment> => {
    const response = await apiClient.post<Experiment>(
      `/experiments/${experimentId}/stop`,
    );
    return response.data;
  },
};

// =============================================================================
// WebSocket for Real-time Updates (v1.1.0)
// =============================================================================

export class RealtimeService {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private listeners: Map<string, Set<(data: unknown) => void>> = new Map();

  connect(): void {
    const wsUrl = import.meta.env.VITE_WS_URL || "ws://localhost:8000/ws";

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log("WebSocket connected");
        this.reconnectAttempts = 0;
      };

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          const { type, data } = message;

          const listeners = this.listeners.get(type);
          if (listeners) {
            listeners.forEach((callback) => callback(data));
          }
        } catch (error) {
          console.error("Failed to parse WebSocket message:", error);
        }
      };

      this.ws.onclose = () => {
        console.log("WebSocket disconnected");
        this.attemptReconnect();
      };

      this.ws.onerror = (error) => {
        console.error("WebSocket error:", error);
      };
    } catch (error) {
      console.error("Failed to connect WebSocket:", error);
    }
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
      setTimeout(() => this.connect(), delay);
    }
  }

  subscribe<T>(eventType: string, callback: (data: T) => void): () => void {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, new Set());
    }

    this.listeners.get(eventType)!.add(callback as (data: unknown) => void);

    // Return unsubscribe function
    return () => {
      this.listeners
        .get(eventType)
        ?.delete(callback as (data: unknown) => void);
    };
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

export const realtimeService = new RealtimeService();

// =============================================================================
// Export Default API
// =============================================================================

export default {
  health: healthApi,
  cities: citiesApi,
  predictions: predictionsApi,
  model: modelApi,
  monitoring: monitoringApi,
  experiments: experimentsApi,
  realtime: realtimeService,
};
