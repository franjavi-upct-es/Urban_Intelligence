// mobile/lib/screens/analytics_screen.dart
// Urban Intelligence Framework v2.0.0
// Analytics screen — listing statistics using fl_chart bar charts

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:fl_chart/fl_chart.dart';
import '../services/providers.dart';
import '../services/api_service.dart';
import '../utils/theme.dart';
import '../widgets/common_widgets.dart';

// ── Providers ─────────────────────────────────────────────────────────────

final _listingsProvider = FutureProvider.family<Map<String, dynamic>, String>(
  (ref, cityId) async {
    final api = ref.read(apiServiceProvider);
    return api.getListings(cityId, limit: 500);
  },
);

// ── Screen ────────────────────────────────────────────────────────────────

class AnalyticsScreen extends ConsumerWidget {
  const AnalyticsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final selectedCity = ref.watch(selectedCityProvider);
    final listingsAsync = ref.watch(_listingsProvider(selectedCity));
    final citiesAsync = ref.watch(citiesProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Analytics'),
        actions: [
          // City quick-select
          citiesAsync.when(
            loading: () => const SizedBox.shrink(),
            error: (_, __) => const SizedBox.shrink(),
            data: (cities) => PopupMenuButton<String>(
              icon: const Icon(Icons.location_city_outlined, size: 20),
              color: AppTheme.surface800,
              onSelected: (v) => ref.read(selectedCityProvider.notifier).set(v),
              itemBuilder: (_) => cities
                  .map((c) => PopupMenuItem(
                        value: c.cityId,
                        child:
                            Text(c.name, style: const TextStyle(fontSize: 13)),
                      ))
                  .toList(),
            ),
          ),
        ],
      ),
      body: listingsAsync.when(
        loading: () => const LoadingView(label: 'Loading listings…'),
        error: (e, _) => ErrorView(
          message: e.toString(),
          onRetry: () => ref.invalidate(_listingsProvider(selectedCity)),
        ),
        data: (data) {
          final listings = (data['listings'] as List<dynamic>?) ?? [];
          if (listings.isEmpty) {
            return const EmptyView(
              icon: Icons.bar_chart_outlined,
              title: 'No data available',
              subtitle: 'Fetch city data first from the Cities tab.',
            );
          }

          final prices = listings
              .map((l) => (l['price'] as num?)?.toDouble())
              .whereType<double>()
              .toList()
            ..sort();

          final roomGroups = _groupBy(
            listings,
            (l) => (l['room_type'] as String?) ?? 'Unknown',
          );

          final total = listings.length;
          final median = prices.isNotEmpty ? prices[prices.length ~/ 2] : 0.0;
          final avg = prices.isNotEmpty
              ? prices.reduce((a, b) => a + b) / prices.length
              : 0.0;

          return RefreshIndicator(
            color: AppTheme.brand500,
            onRefresh: () async =>
                ref.invalidate(_listingsProvider(selectedCity)),
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                // ── Summary cards ────────────────────────────────────
                Row(children: [
                  Expanded(child: StatCard(title: 'Listings', value: '$total')),
                  const SizedBox(width: 10),
                  Expanded(
                      child: StatCard(
                          title: 'Median Price',
                          value: '\$${median.toStringAsFixed(0)}')),
                  const SizedBox(width: 10),
                  Expanded(
                      child: StatCard(
                          title: 'Avg Price',
                          value: '\$${avg.toStringAsFixed(0)}')),
                ]),

                const SizedBox(height: 20),

                // ── Price histogram ───────────────────────────────────
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const SectionTitle('Price Distribution'),
                        const SizedBox(height: 16),
                        SizedBox(
                          height: 180,
                          child: _PriceHistogram(prices: prices),
                        ),
                      ],
                    ),
                  ),
                ),

                const SizedBox(height: 14),

                // ── Room type breakdown ───────────────────────────────
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const SectionTitle('Room Type Breakdown'),
                        const SizedBox(height: 12),
                        ...roomGroups.entries.map((entry) {
                          final pct = entry.value / total;
                          return Padding(
                            padding: const EdgeInsets.only(bottom: 10),
                            child: ProgressRow(
                              label: '${entry.key} (${entry.value})',
                              value: pct,
                            ),
                          );
                        }),
                      ],
                    ),
                  ),
                ),

                const SizedBox(height: 80),
              ],
            ),
          );
        },
      ),
    );
  }

  Map<String, int> _groupBy(List<dynamic> items, String Function(dynamic) key) {
    final result = <String, int>{};
    for (final item in items) {
      final k = key(item);
      result[k] = (result[k] ?? 0) + 1;
    }
    return Map.fromEntries(
      result.entries.toList()..sort((a, b) => b.value.compareTo(a.value)),
    );
  }
}

// ── Price histogram using fl_chart ────────────────────────────────────────

class _PriceHistogram extends StatelessWidget {
  final List<double> prices;
  const _PriceHistogram({required this.prices});

  List<BarChartGroupData> _buildBars() {
    if (prices.isEmpty) return [];
    const bins = 10;
    final min = prices.first;
    final max = prices.last;
    final step = (max - min) / bins;
    final counts = List<int>.filled(bins, 0);
    for (final p in prices) {
      final idx = ((p - min) / step).floor().clamp(0, bins - 1);
      counts[idx]++;
    }
    return List.generate(
      bins,
      (i) => BarChartGroupData(
        x: i,
        barRods: [
          BarChartRodData(
            toY: counts[i].toDouble(),
            color: AppTheme.brand500,
            width: 14,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(3)),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (prices.isEmpty) return const SizedBox.shrink();
    return BarChart(
      BarChartData(
        barGroups: _buildBars(),
        gridData: FlGridData(
          show: true,
          drawVerticalLine: false,
          getDrawingHorizontalLine: (_) =>
              const FlLine(color: AppTheme.border, strokeWidth: 0.5),
        ),
        borderData: FlBorderData(show: false),
        titlesData: FlTitlesData(
          leftTitles:
              const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          rightTitles:
              const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          topTitles:
              const AxisTitles(sideTitles: SideTitles(showTitles: false)),
          bottomTitles: AxisTitles(
            sideTitles: SideTitles(
              showTitles: true,
              getTitlesWidget: (v, _) {
                if (v.toInt() % 2 != 0) return const SizedBox.shrink();
                final min = prices.first;
                final max = prices.last;
                final val = min + (v / 10) * (max - min);
                return Text(
                  '\$${val.toStringAsFixed(0)}',
                  style:
                      const TextStyle(fontSize: 9, color: AppTheme.textMuted),
                );
              },
            ),
          ),
        ),
        barTouchData: BarTouchData(
          touchTooltipData: BarTouchTooltipData(
            getTooltipColor: (_) => AppTheme.surface800,
            getTooltipItem: (_, __, rod, ___) => BarTooltipItem(
              '${rod.toY.toInt()} listings',
              const TextStyle(fontSize: 12, color: AppTheme.textPrimary),
            ),
          ),
        ),
      ),
    );
  }
}
