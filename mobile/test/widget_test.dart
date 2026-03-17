// mobile/test/widget_test.dart
// Urban Intelligence Framework v2.0.0
// Flutter widget and unit tests

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:urban_intelligence/main.dart';
import 'package:urban_intelligence/models/city.dart';
import 'package:urban_intelligence/models/prediction.dart';
import 'package:urban_intelligence/models/monitoring.dart';

// ── Model serialisation tests ─────────────────────────────────────────────

void main() {
  group('City model', () {
    test('fromJson parses all fields', () {
      final json = {
        'city_id': 'london',
        'name': 'London',
        'country': 'United Kingdom',
        'latitude': 51.5074,
        'longitude': -0.1278,
        'currency': 'GBP',
        'is_cached': true,
        'listing_count': 3500,
      };
      final city = City.fromJson(json);

      expect(city.cityId, 'london');
      expect(city.name, 'London');
      expect(city.country, 'United Kingdom');
      expect(city.latitude, 51.5074);
      expect(city.longitude, -0.1278);
      expect(city.currency, 'GBP');
      expect(city.isCached, true);
      expect(city.listingCount, 3500);
    });

    test('fromJson handles null listingCount', () {
      final json = {
        'city_id': 'paris',
        'name': 'Paris',
        'country': 'France',
        'latitude': 48.8566,
        'longitude': 2.3522,
        'currency': 'EUR',
        'is_cached': false,
      };
      final city = City.fromJson(json);
      expect(city.listingCount, isNull);
    });

    test('toJson round-trips correctly', () {
      const city = City(
        cityId: 'berlin',
        name: 'Berlin',
        country: 'Germany',
        latitude: 52.52,
        longitude: 13.4,
        currency: 'EUR',
        isCached: false,
      );
      final json = city.toJson();
      final restored = City.fromJson(json);
      expect(restored.cityId, city.cityId);
      expect(restored.name, city.name);
    });
  });

  group('PredictionRequest model', () {
    test('toJson serialises all fields', () {
      const req = PredictionRequest(
        cityId: 'london',
        roomType: 'Entire home/apt',
        accommodates: 2,
        bedrooms: 1,
        beds: 1,
        bathrooms: 1.0,
        amenityCount: 10,
        reviewScoresRating: 4.5,
        numberOfReviews: 20,
        availability365: 200,
        minimumNights: 2,
        hostIsSuperhost: false,
        instantBookable: true,
        latitude: 51.5,
        longitude: -0.12,
      );
      final json = req.toJson();
      expect(json['city_id'], 'london');
      expect(json['room_type'], 'Entire home/apt');
      expect(json['bedrooms'], 1);
      expect(json['bathrooms'], 1.0);
      expect(json['instant_bookable'], true);
    });

    test('copyWith creates modified copy', () {
      const req = PredictionRequest(
        cityId: 'london',
        roomType: 'Entire home/apt',
        accommodates: 2,
        bedrooms: 1,
        beds: 1,
        bathrooms: 1.0,
        amenityCount: 10,
        reviewScoresRating: 4.5,
        numberOfReviews: 20,
        availability365: 200,
        minimumNights: 2,
        hostIsSuperhost: false,
        instantBookable: false,
        latitude: 51.5,
        longitude: -0.12,
      );
      final modified = req.copyWith(bedrooms: 3, cityId: 'paris');
      expect(modified.bedrooms, 3);
      expect(modified.cityId, 'paris');
      // Unchanged fields preserved
      expect(modified.accommodates, 2);
    });
  });

  group('PredictionResult model', () {
    test('fromJson parses correctly', () {
      final json = {
        'prediction_id': 'pred_abc123',
        'city_id': 'london',
        'predicted_price': 145.50,
        'currency': 'USD',
        'confidence_interval': {'lower': 120.0, 'upper': 175.0},
        'latency_ms': 42.5,
        'model_version': '2.0.0',
      };
      final result = PredictionResult.fromJson(json);
      expect(result.predictedPrice, 145.50);
      expect(result.confidenceInterval.lower, 120.0);
      expect(result.confidenceInterval.upper, 175.0);
      expect(result.confidenceInterval.range, closeTo(55.0, 0.001));
    });
  });

  group('MonitoringSnapshot model', () {
    test('fromJson parses with nullable fields', () {
      final json = {
        'city_id': 'london',
        'timestamp': '2026-01-01T12:00:00',
        'rmse': null,
        'mae': null,
        'r2': null,
        'avg_latency_ms': null,
        'p95_latency_ms': null,
        'request_rate': 5.0,
        'error_rate': 0.01,
        'n_predictions': 0,
        'active_alerts': <dynamic>[],
      };
      final snap = MonitoringSnapshot.fromJson(json);
      expect(snap.rmse, isNull);
      expect(snap.nPredictions, 0);
      expect(snap.hasAlerts, false);
      expect(snap.errorRate, 0.01);
    });

    test('hasCriticalAlerts detects critical severity', () {
      final json = {
        'city_id': 'london',
        'timestamp': '2026-01-01T00:00:00',
        'rmse': 0.5,
        'mae': 0.3,
        'r2': 0.8,
        'avg_latency_ms': 50.0,
        'p95_latency_ms': 100.0,
        'request_rate': 10.0,
        'error_rate': 0.02,
        'n_predictions': 100,
        'active_alerts': [
          {
            'alert_id': 'alert_001',
            'city_id': 'london',
            'metric': 'rmse',
            'current_value': 0.7,
            'threshold': 0.5,
            'severity': 'critical',
            'message': 'RMSE is too high',
            'created_at': '2026-01-01T00:00:00',
          }
        ],
      };
      final snap = MonitoringSnapshot.fromJson(json);
      expect(snap.hasAlerts, true);
      expect(snap.hasCriticalAlerts, true);
    });
  });

  // ── Widget smoke test ─────────────────────────────────────────────────

  testWidgets('App renders without errors', (tester) async {
    await tester.pumpWidget(
      const ProviderScope(child: UrbanIntelligenceApp()),
    );
    // App should render a scaffold with bottom nav
    expect(find.byType(NavigationBar), findsOneWidget);
  });
}
