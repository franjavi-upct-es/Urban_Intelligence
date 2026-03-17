// mobile/lib/services/providers.dart
// Urban Intelligence Framework v2.0.0
// Riverpod providers for app-wide state management

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../models/city.dart';
import '../models/prediction.dart';
import '../models/monitoring.dart';
import 'api_service.dart';

// ── Settings ──────────────────────────────────────────────────────────────

/// Currently selected city (persisted via SharedPreferences).
final selectedCityProvider =
    StateNotifierProvider<SelectedCityNotifier, String>(
  (ref) => SelectedCityNotifier(),
);

class SelectedCityNotifier extends StateNotifier<String> {
  SelectedCityNotifier() : super('london') {
    _load();
  }

  Future<void> _load() async {
    final prefs = await SharedPreferences.getInstance();
    state = prefs.getString('selected_city') ?? 'london';
  }

  Future<void> set(String cityId) async {
    state = cityId;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('selected_city', cityId);
  }
}

// ── Cities ────────────────────────────────────────────────────────────────

/// Async provider that fetches the full city catalogue.
final citiesProvider = FutureProvider<List<City>>((ref) async {
  final api = ref.read(apiServiceProvider);
  return api.getCities();
});

/// Refresh trigger for cities (increment to force re-fetch).
final citiesRefreshProvider = StateProvider<int>((ref) => 0);

/// Cities list that re-fetches when the refresh counter changes.
final citiesRefreshableProvider = FutureProvider<List<City>>((ref) async {
  ref.watch(citiesRefreshProvider);
  final api = ref.read(apiServiceProvider);
  return api.getCities();
});

// ── Predictions ───────────────────────────────────────────────────────────

/// State of the prediction form.
final predictionRequestProvider = StateProvider<PredictionRequest>((ref) {
  final city = ref.watch(selectedCityProvider);
  return PredictionRequest(
    cityId: city,
    roomType: 'Entire home/apt',
    accommodates: 2,
    bedrooms: 1,
    beds: 1,
    bathrooms: 1.0,
    amenityCount: 12,
    reviewScoresRating: 4.5,
    numberOfReviews: 25,
    availability365: 200,
    minimumNights: 2,
    hostIsSuperhost: false,
    instantBookable: false,
    latitude: 51.5074,
    longitude: -0.1278,
  );
});

/// The most recent prediction result (null until a prediction is made).
final latestPredictionProvider =
    StateProvider<PredictionResult?>((ref) => null);

/// Prediction loading/error state.
final predictionStateProvider = StateProvider<AsyncValue<PredictionResult?>>(
    (ref) => const AsyncValue.data(null));

// ── Monitoring ────────────────────────────────────────────────────────────

/// Monitoring snapshot for the currently selected city.
final monitoringSnapshotProvider =
    FutureProvider<MonitoringSnapshot>((ref) async {
  final city = ref.watch(selectedCityProvider);
  final api = ref.read(apiServiceProvider);
  return api.getSnapshot(city);
});

/// All active alerts across cities.
final allAlertsProvider = FutureProvider<List<Alert>>((ref) async {
  final api = ref.read(apiServiceProvider);
  return api.getAlerts();
});

// ── Prediction history ────────────────────────────────────────────────────

final predictionHistoryProvider =
    FutureProvider<List<PredictionResult>>((ref) async {
  final api = ref.read(apiServiceProvider);
  return api.getPredictionHistory(limit: 30);
});

// ── API health ────────────────────────────────────────────────────────────

final apiHealthProvider = FutureProvider<bool>((ref) async {
  final api = ref.read(apiServiceProvider);
  return api.isHealthy();
});
