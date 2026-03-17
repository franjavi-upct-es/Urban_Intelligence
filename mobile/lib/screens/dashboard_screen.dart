// mobile/lib/screens/dashboard_screen.dart
// Urban Intelligence Framework v2.0.0
// Dashboard screen — overview KPIs, city status, recent predictions

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/providers.dart';
import '../utils/theme.dart';
import '../widgets/common_widgets.dart';

class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final citiesAsync = ref.watch(citiesRefreshableProvider);
    final alertsAsync = ref.watch(allAlertsProvider);
    final historyAsync = ref.watch(predictionHistoryProvider);
    final selectedCity = ref.watch(selectedCityProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Dashboard'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, size: 20),
            onPressed: () {
              ref.invalidate(citiesRefreshableProvider);
              ref.invalidate(allAlertsProvider);
              ref.invalidate(predictionHistoryProvider);
            },
          ),
        ],
      ),
      body: RefreshIndicator(
        color: AppTheme.brand500,
        onRefresh: () async {
          ref.invalidate(citiesRefreshableProvider);
          ref.invalidate(allAlertsProvider);
        },
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // ── Header ───────────────────────────────────────────────
              _Header(selectedCity: selectedCity),
              const SizedBox(height: 16),

              // ── KPI grid ──────────────────────────────────────────────
              citiesAsync.when(
                loading: () => const LoadingView(label: 'Loading cities…'),
                error: (e, _) => ErrorView(message: e.toString()),
                data: (cities) {
                  final cached = cities.where((c) => c.isCached).length;
                  return Column(
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: StatCard(
                              title: 'Total Cities',
                              value: '${cities.length}',
                              subtitle: 'in catalogue',
                              icon: Icons.map_outlined,
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: StatCard(
                              title: 'Cached',
                              value: '$cached',
                              subtitle: 'data ready',
                              icon: Icons.storage_outlined,
                              valueColor: AppTheme.success,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 10),
                      Row(
                        children: [
                          Expanded(
                            child: historyAsync.when(
                              loading: () => const StatCard(
                                  title: 'Predictions', value: '—'),
                              error: (_, __) => const StatCard(
                                  title: 'Predictions', value: '—'),
                              data: (history) => StatCard(
                                title: 'Recent Preds',
                                value: '${history.length}',
                                subtitle: 'last 30',
                                icon: Icons.trending_up_outlined,
                              ),
                            ),
                          ),
                          const SizedBox(width: 10),
                          Expanded(
                            child: alertsAsync.when(
                              loading: () =>
                                  const StatCard(title: 'Alerts', value: '—'),
                              error: (_, __) =>
                                  const StatCard(title: 'Alerts', value: '—'),
                              data: (alerts) => StatCard(
                                title: 'Active Alerts',
                                value: '${alerts.length}',
                                subtitle: alerts.isEmpty
                                    ? 'all clear'
                                    : 'attention needed',
                                icon: alerts.isEmpty
                                    ? Icons.check_circle_outline
                                    : Icons.warning_amber_outlined,
                                valueColor: alerts.isEmpty
                                    ? AppTheme.success
                                    : AppTheme.warning,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ],
                  );
                },
              ),

              const SizedBox(height: 20),

              // ── City status list ───────────────────────────────────────
              const SectionTitle('City Status'),
              const SizedBox(height: 10),
              citiesAsync.when(
                loading: () => const LoadingView(),
                error: (e, _) => ErrorView(message: e.toString()),
                data: (cities) => Card(
                  child: ListView.separated(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    itemCount: cities.length,
                    separatorBuilder: (_, __) => const Divider(height: 1),
                    itemBuilder: (context, i) {
                      final city = cities[i];
                      return ListTile(
                        dense: true,
                        leading: CircleAvatar(
                          radius: 16,
                          backgroundColor: city.isCached
                              ? AppTheme.success.withAlpha((0.15 * 255).round())
                              : AppTheme.border,
                          child: Icon(
                            city.isCached
                                ? Icons.check
                                : Icons.cloud_download_outlined,
                            size: 14,
                            color: city.isCached
                                ? AppTheme.success
                                : AppTheme.textMuted,
                          ),
                        ),
                        title: Text(
                          city.name,
                          style: const TextStyle(
                              fontSize: 13, fontWeight: FontWeight.w500),
                        ),
                        subtitle: Text(
                          city.country,
                          style: const TextStyle(
                              fontSize: 11, color: AppTheme.textMuted),
                        ),
                        trailing: StatusBadge(
                          city.isCached ? 'cached' : 'not fetched',
                          variant: city.isCached
                              ? BadgeVariant.green
                              : BadgeVariant.gray,
                        ),
                      );
                    },
                  ),
                ),
              ),

              const SizedBox(height: 20),

              // ── Recent predictions ────────────────────────────────────
              const SectionTitle('Recent Predictions'),
              const SizedBox(height: 10),
              historyAsync.when(
                loading: () => const LoadingView(),
                error: (_, __) => const SizedBox.shrink(),
                data: (history) => history.isEmpty
                    ? const EmptyView(
                        icon: Icons.trending_up_outlined,
                        title: 'No predictions yet',
                        subtitle:
                            'Use the Predict tab to generate price estimates.',
                      )
                    : Card(
                        child: ListView.separated(
                          shrinkWrap: true,
                          physics: const NeverScrollableScrollPhysics(),
                          itemCount: history.take(5).length,
                          separatorBuilder: (_, __) => const Divider(height: 1),
                          itemBuilder: (context, i) {
                            final p = history[i];
                            return ListTile(
                              dense: true,
                              title: Text(
                                '\$${p.predictedPrice.toStringAsFixed(2)}',
                                style: const TextStyle(
                                  fontSize: 14,
                                  fontWeight: FontWeight.w700,
                                  color: AppTheme.brand500,
                                ),
                              ),
                              subtitle: Text(
                                p.cityId,
                                style: const TextStyle(
                                    fontSize: 11, color: AppTheme.textMuted),
                              ),
                              trailing: Text(
                                '${p.latencyMs.toStringAsFixed(1)}ms',
                                style: const TextStyle(
                                    fontSize: 11, color: AppTheme.textMuted),
                              ),
                            );
                          },
                        ),
                      ),
              ),

              const SizedBox(height: 80), // bottom nav clearance
            ],
          ),
        ),
      ),
    );
  }
}

// ── Header widget ─────────────────────────────────────────────────────────

class _Header extends StatelessWidget {
  final String selectedCity;
  const _Header({required this.selectedCity});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            AppTheme.brand600.withAlpha((0.3 * 255).round()),
            AppTheme.surface800
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(12),
        border:
            Border.all(color: AppTheme.brand500.withAlpha((0.2 * 255).round())),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: AppTheme.brand600,
              borderRadius: BorderRadius.circular(10),
            ),
            child: const Icon(Icons.psychology, color: Colors.white, size: 22),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Urban Intelligence',
                  style: TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.w700,
                    color: AppTheme.textPrimary,
                  ),
                ),
                Text(
                  'City: $selectedCity · v2.0.0',
                  style:
                      const TextStyle(fontSize: 12, color: AppTheme.textMuted),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
