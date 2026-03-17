// mobile/lib/services/api_service.dart
// Urban Intelligence Framework v2.0.0
// Centralised HTTP API service for the mobile app

import 'dart:convert';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;
import '../models/city.dart';
import '../models/prediction.dart';
import '../models/monitoring.dart';

// ── Provider ──────────────────────────────────────────────────────────────

final apiServiceProvider = Provider<ApiService>((ref) => ApiService());

// ── Service ───────────────────────────────────────────────────────────────

class ApiService {
  // Default to localhost; override in production via .env or --dart-define
  static const String _base = String.fromEnvironment('API_URL',
      defaultValue: 'http://localhost:8000/api/v1');

  final _client = http.Client();

  // ── Cities ───────────────────────────────────────────────────────────

  /// Fetch the list of all available cities from the catalogue.
  Future<List<City>> getCities() async {
    final response = await _get('/cities/');
    final List<dynamic> data = jsonDecode(response.body) as List<dynamic>;
    return data
        .map((json) => City.fromJson(json as Map<String, dynamic>))
        .toList();
  }

  /// Trigger a data fetch for a single city in the background.
  Future<Map<String, dynamic>> fetchCity(String cityId,
      {bool force = false}) async {
    final response = await _post(
      '/cities/$cityId/fetch',
      {'force_refresh': force},
    );
    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  /// Get cached listings for a city.
  Future<Map<String, dynamic>> getListings(
    String cityId, {
    int limit = 100,
    String? roomType,
  }) async {
    final params = <String, String>{'limit': '$limit'};
    if (roomType != null) params['room_type'] = roomType;
    final response = await _get('/cities/$cityId/listings', params: params);
    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  // ── Predictions ──────────────────────────────────────────────────────

  /// Run a single listing price prediction.
  Future<PredictionResult> predictSingle(PredictionRequest request) async {
    final response = await _post('/predictions/single', request.toJson());
    return PredictionResult.fromJson(
        jsonDecode(response.body) as Map<String, dynamic>);
  }

  /// Fetch recent prediction history.
  Future<List<PredictionResult>> getPredictionHistory({int limit = 20}) async {
    final response =
        await _get('/predictions/history', params: {'limit': '$limit'});
    final data = jsonDecode(response.body) as Map<String, dynamic>;
    final history = data['history'] as List<dynamic>;
    return history
        .map((json) => PredictionResult.fromJson(json as Map<String, dynamic>))
        .toList();
  }

  // ── Monitoring ───────────────────────────────────────────────────────

  /// Get the monitoring snapshot for a city.
  Future<MonitoringSnapshot> getSnapshot(String cityId) async {
    final response = await _get('/monitoring/snapshot/$cityId');
    return MonitoringSnapshot.fromJson(
        jsonDecode(response.body) as Map<String, dynamic>);
  }

  /// Get all active alerts.
  Future<List<Alert>> getAlerts() async {
    final response = await _get('/monitoring/alerts');
    final data = jsonDecode(response.body) as Map<String, dynamic>;
    final alerts = data['alerts'] as List<dynamic>;
    return alerts
        .map((json) => Alert.fromJson(json as Map<String, dynamic>))
        .toList();
  }

  // ── Health ───────────────────────────────────────────────────────────

  /// Check if the backend is reachable and healthy.
  Future<bool> isHealthy() async {
    try {
      final uri = Uri.parse('${_base.replaceFirst('/api/v1', '')}/health');
      final response =
          await _client.get(uri).timeout(const Duration(seconds: 5));
      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  // ── Private helpers ──────────────────────────────────────────────────

  Future<http.Response> _get(
    String path, {
    Map<String, String>? params,
  }) async {
    final uri = Uri.parse('$_base$path').replace(queryParameters: params);
    final response = await _client
        .get(uri, headers: _headers)
        .timeout(const Duration(seconds: 30));
    _throwOnError(response);
    return response;
  }

  Future<http.Response> _post(String path, Map<String, dynamic> body) async {
    final uri = Uri.parse('$_base$path');
    final response = await _client
        .post(uri, headers: _headers, body: jsonEncode(body))
        .timeout(const Duration(seconds: 30));
    _throwOnError(response);
    return response;
  }

  static const Map<String, String> _headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  };

  void _throwOnError(http.Response response) {
    if (response.statusCode >= 400) {
      String message = 'HTTP ${response.statusCode}';
      try {
        final data = jsonDecode(response.body) as Map<String, dynamic>;
        message = data['detail']?.toString() ?? message;
      } catch (_) {}
      throw ApiException(message, response.statusCode);
    }
  }

  void dispose() => _client.close();
}

// ── Custom exception ──────────────────────────────────────────────────────

class ApiException implements Exception {
  final String message;
  final int statusCode;
  const ApiException(this.message, this.statusCode);

  @override
  String toString() => 'ApiException($statusCode): $message';
}
