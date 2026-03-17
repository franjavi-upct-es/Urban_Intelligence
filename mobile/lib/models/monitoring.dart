// mobile/lib/models/monitoring.dart
// Urban Intelligence Framework v2.0.0
// Monitoring snapshot and alert data models

class Alert {
  final String alertId;
  final String? cityId;
  final String metric;
  final double currentValue;
  final double threshold;
  final String severity; // "warning" | "critical"
  final String message;
  final String createdAt;

  const Alert({
    required this.alertId,
    this.cityId,
    required this.metric,
    required this.currentValue,
    required this.threshold,
    required this.severity,
    required this.message,
    required this.createdAt,
  });

  factory Alert.fromJson(Map<String, dynamic> json) => Alert(
        alertId: json['alert_id'] as String,
        cityId: json['city_id'] as String?,
        metric: json['metric'] as String,
        currentValue: (json['current_value'] as num).toDouble(),
        threshold: (json['threshold'] as num).toDouble(),
        severity: json['severity'] as String,
        message: json['message'] as String,
        createdAt: json['created_at'] as String,
      );

  bool get isCritical => severity == 'critical';
}

class MonitoringSnapshot {
  final String cityId;
  final String timestamp;
  final double? rmse;
  final double? mae;
  final double? r2;
  final double? avgLatencyMs;
  final double? p95LatencyMs;
  final double requestRate;
  final double errorRate;
  final int nPredictions;
  final List<Alert> activeAlerts;

  const MonitoringSnapshot({
    required this.cityId,
    required this.timestamp,
    this.rmse,
    this.mae,
    this.r2,
    this.avgLatencyMs,
    this.p95LatencyMs,
    required this.requestRate,
    required this.errorRate,
    required this.nPredictions,
    required this.activeAlerts,
  });

  factory MonitoringSnapshot.fromJson(Map<String, dynamic> json) =>
      MonitoringSnapshot(
        cityId: json['city_id'] as String,
        timestamp: json['timestamp'] as String,
        rmse: (json['rmse'] as num?)?.toDouble(),
        mae: (json['mae'] as num?)?.toDouble(),
        r2: (json['r2'] as num?)?.toDouble(),
        avgLatencyMs: (json['avg_latency_ms'] as num?)?.toDouble(),
        p95LatencyMs: (json['p95_latency_ms'] as num?)?.toDouble(),
        requestRate: (json['request_rate'] as num).toDouble(),
        errorRate: (json['error_rate'] as num).toDouble(),
        nPredictions: json['n_predictions'] as int,
        activeAlerts: (json['active_alerts'] as List<dynamic>)
            .map((a) => Alert.fromJson(a as Map<String, dynamic>))
            .toList(),
      );

  bool get hasAlerts => activeAlerts.isNotEmpty;
  bool get hasCriticalAlerts => activeAlerts.any((a) => a.isCritical);
}
