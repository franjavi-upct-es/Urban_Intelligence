// mobile/lib/screens/monitoring_screen.dart
// Urban Intelligence Framework v2.0.0
// Model monitoring screen — snapshot metrics and active alerts

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/providers.dart';
import '../models/monitoring.dart';
import '../utils/theme.dart';
import '../widgets/common_widgets.dart';

class MonitoringScreen extends ConsumerWidget {
  const MonitoringScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final selectedCity = ref.watch(selectedCityProvider);
    final snapshotAsync = ref.watch(monitoringSnapshotProvider);
    final alertsAsync = ref.watch(allAlertsProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Monitoring'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, size: 20),
            onPressed: () {
              ref.invalidate(monitoringSnapshotProvider);
              ref.invalidate(allAlertsProvider);
            },
          ),
        ],
      ),
      body: RefreshIndicator(
        color: AppTheme.brand500,
        onRefresh: () async {
          ref.invalidate(monitoringSnapshotProvider);
          ref.invalidate(allAlertsProvider);
        },
        child: ListView(
          padding: const EdgeInsets.all(16),
          physics: const AlwaysScrollableScrollPhysics(),
          children: [
            // ── City indicator ────────────────────────────────────────
            Row(
              children: [
                const Icon(Icons.location_on_outlined,
                    size: 14, color: AppTheme.textMuted),
                const SizedBox(width: 4),
                Text(
                  'Monitoring: $selectedCity',
                  style:
                      const TextStyle(fontSize: 12, color: AppTheme.textMuted),
                ),
              ],
            ),
            const SizedBox(height: 16),

            // ── Snapshot metrics ──────────────────────────────────────
            snapshotAsync.when(
              loading: () => const LoadingView(label: 'Loading snapshot…'),
              error: (e, _) => ErrorView(
                message: e.toString(),
                onRetry: () => ref.invalidate(monitoringSnapshotProvider),
              ),
              data: (snap) => _SnapshotSection(snapshot: snap),
            ),

            const SizedBox(height: 20),

            // ── All active alerts ─────────────────────────────────────
            const SectionTitle('Active Alerts'),
            const SizedBox(height: 10),
            alertsAsync.when(
              loading: () => const LoadingView(),
              error: (e, _) => ErrorView(message: e.toString()),
              data: (alerts) => alerts.isEmpty
                  ? _AllClearCard()
                  : Column(
                      children:
                          alerts.map((a) => _AlertCard(alert: a)).toList(),
                    ),
            ),

            const SizedBox(height: 80),
          ],
        ),
      ),
    );
  }
}

// ── Snapshot section ──────────────────────────────────────────────────────

class _SnapshotSection extends StatelessWidget {
  final MonitoringSnapshot snapshot;
  const _SnapshotSection({required this.snapshot});

  String _fmt(double? v, {int decimals = 4}) =>
      v != null ? v.toStringAsFixed(decimals) : '—';

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SectionTitle('Model Performance'),
        const SizedBox(height: 10),
        Row(
          children: [
            Expanded(
                child: StatCard(
                    title: 'RMSE',
                    value: _fmt(snapshot.rmse),
                    subtitle: 'lower is better')),
            const SizedBox(width: 10),
            Expanded(
                child: StatCard(
                    title: 'MAE',
                    value: _fmt(snapshot.mae),
                    subtitle: 'mean abs error')),
          ],
        ),
        const SizedBox(height: 10),
        Row(
          children: [
            Expanded(
                child: StatCard(
                    title: 'R²',
                    value: _fmt(snapshot.r2),
                    subtitle: 'variance explained')),
            const SizedBox(width: 10),
            Expanded(
                child: StatCard(
                    title: 'Predictions',
                    value: '${snapshot.nPredictions}',
                    subtitle: 'total')),
          ],
        ),
        const SizedBox(height: 10),
        Row(
          children: [
            Expanded(
                child: StatCard(
                    title: 'Avg Latency',
                    value: snapshot.avgLatencyMs != null
                        ? '${snapshot.avgLatencyMs!.toStringAsFixed(1)}ms'
                        : '—')),
            const SizedBox(width: 10),
            Expanded(
                child: StatCard(
                    title: 'Error Rate',
                    value:
                        '${(snapshot.errorRate * 100).toStringAsFixed(2)}%')),
          ],
        ),
        if (snapshot.hasAlerts) ...[
          const SizedBox(height: 16),
          const SectionTitle('City Alerts'),
          const SizedBox(height: 8),
          ...snapshot.activeAlerts.map((a) => _AlertCard(alert: a)),
        ],
      ],
    );
  }
}

// ── Alert card ────────────────────────────────────────────────────────────

class _AlertCard extends StatelessWidget {
  final Alert alert;
  const _AlertCard({required this.alert});

  @override
  Widget build(BuildContext context) {
    final isCritical = alert.isCritical;
    final borderColor = isCritical
        ? AppTheme.error.withAlpha((0.5 * 255).round())
        : AppTheme.warning.withAlpha((0.5 * 255).round());
    final bgColor = isCritical
        ? AppTheme.error.withAlpha((0.08 * 255).round())
        : AppTheme.warning.withAlpha((0.08 * 255).round());
    final iconColor = isCritical ? AppTheme.error : AppTheme.warning;

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: borderColor),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            isCritical ? Icons.error_outline : Icons.warning_amber_outlined,
            color: iconColor,
            size: 18,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  alert.message,
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w500,
                    color: AppTheme.textPrimary,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  'Metric: ${alert.metric} · Value: ${alert.currentValue.toStringAsFixed(4)}',
                  style:
                      const TextStyle(fontSize: 11, color: AppTheme.textMuted),
                ),
                if (alert.cityId != null)
                  Text(
                    'City: ${alert.cityId}',
                    style: const TextStyle(
                        fontSize: 11, color: AppTheme.textMuted),
                  ),
              ],
            ),
          ),
          StatusBadge(
            alert.severity,
            variant: isCritical ? BadgeVariant.red : BadgeVariant.yellow,
          ),
        ],
      ),
    );
  }
}

// ── All clear card ────────────────────────────────────────────────────────

class _AllClearCard extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.success.withAlpha((0.08 * 255).round()),
        borderRadius: BorderRadius.circular(10),
        border:
            Border.all(color: AppTheme.success.withAlpha((0.3 * 255).round())),
      ),
      child: const Row(
        children: [
          Icon(Icons.check_circle_outline, color: AppTheme.success, size: 20),
          SizedBox(width: 10),
          Text(
            'All clear — no active alerts',
            style: TextStyle(
                fontSize: 13,
                color: AppTheme.success,
                fontWeight: FontWeight.w500),
          ),
        ],
      ),
    );
  }
}
