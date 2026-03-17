// mobile/lib/screens/cities_screen.dart
// Urban Intelligence Framework v2.0.0
// Cities catalogue and data fetch management screen

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/city.dart';
import '../services/providers.dart';
import '../services/api_service.dart';
import '../utils/theme.dart';
import '../widgets/common_widgets.dart';

class CitiesScreen extends ConsumerStatefulWidget {
  const CitiesScreen({super.key});

  @override
  ConsumerState<CitiesScreen> createState() => _CitiesScreenState();
}

class _CitiesScreenState extends ConsumerState<CitiesScreen> {
  final _fetchingCities = <String>{};
  final _fetchMessages = <String, String>{};

  Future<void> _fetchCity(String cityId, {bool force = false}) async {
    setState(() {
      _fetchingCities.add(cityId);
      _fetchMessages[cityId] = force ? 'Refreshing…' : 'Fetching data…';
    });
    try {
      final api = ref.read(apiServiceProvider);
      await api.fetchCity(cityId, force: force);
      setState(() => _fetchMessages[cityId] = 'Fetch triggered!');
      await Future<void>.delayed(const Duration(seconds: 2));
      ref.invalidate(citiesRefreshableProvider);
    } on ApiException catch (e) {
      setState(() => _fetchMessages[cityId] = 'Error: ${e.message}');
    } finally {
      setState(() => _fetchingCities.remove(cityId));
    }
  }

  @override
  Widget build(BuildContext context) {
    final citiesAsync = ref.watch(citiesRefreshableProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Cities'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, size: 20),
            onPressed: () => ref.invalidate(citiesRefreshableProvider),
          ),
        ],
      ),
      body: citiesAsync.when(
        loading: () => const LoadingView(label: 'Loading cities…'),
        error: (e, _) => ErrorView(
          message: e.toString(),
          onRetry: () => ref.invalidate(citiesRefreshableProvider),
        ),
        data: (cities) {
          final cached = cities.where((c) => c.isCached).toList();
          final notCached = cities.where((c) => !c.isCached).toList();

          return RefreshIndicator(
            color: AppTheme.brand500,
            onRefresh: () async => ref.invalidate(citiesRefreshableProvider),
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                // ── Summary row ──────────────────────────────────────
                Row(
                  children: [
                    Expanded(
                      child: StatCard(
                        title: 'Total Cities',
                        value: '${cities.length}',
                        icon: Icons.map_outlined,
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: StatCard(
                        title: 'Cached',
                        value: '${cached.length}',
                        icon: Icons.storage_outlined,
                        valueColor: AppTheme.success,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 20),

                // ── Cached cities ────────────────────────────────────
                if (cached.isNotEmpty) ...[
                  const SectionTitle('Cached Cities'),
                  const SizedBox(height: 8),
                  ...cached.map((c) => _CityTile(
                        city: c,
                        isFetching: _fetchingCities.contains(c.cityId),
                        statusMessage: _fetchMessages[c.cityId],
                        onFetch: (force) => _fetchCity(c.cityId, force: force),
                        onSelect: () => ref
                            .read(selectedCityProvider.notifier)
                            .set(c.cityId),
                        isSelected: ref.watch(selectedCityProvider) == c.cityId,
                      )),
                  const SizedBox(height: 20),
                ],

                // ── Not yet fetched ──────────────────────────────────
                if (notCached.isNotEmpty) ...[
                  const SectionTitle('Available to Download'),
                  const SizedBox(height: 8),
                  ...notCached.map((c) => _CityTile(
                        city: c,
                        isFetching: _fetchingCities.contains(c.cityId),
                        statusMessage: _fetchMessages[c.cityId],
                        onFetch: (force) => _fetchCity(c.cityId, force: force),
                        onSelect: () => ref
                            .read(selectedCityProvider.notifier)
                            .set(c.cityId),
                        isSelected: ref.watch(selectedCityProvider) == c.cityId,
                      )),
                ],

                const SizedBox(height: 80),
              ],
            ),
          );
        },
      ),
    );
  }
}

// ── City tile ─────────────────────────────────────────────────────────────

class _CityTile extends StatelessWidget {
  final City city;
  final bool isFetching;
  final String? statusMessage;
  final void Function(bool force) onFetch;
  final VoidCallback onSelect;
  final bool isSelected;

  const _CityTile({
    required this.city,
    required this.isFetching,
    this.statusMessage,
    required this.onFetch,
    required this.onSelect,
    required this.isSelected,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onSelect,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        margin: const EdgeInsets.only(bottom: 8),
        decoration: BoxDecoration(
          color: AppTheme.surface800,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isSelected
                ? AppTheme.brand500.withAlpha((0.6 * 255).round())
                : AppTheme.border,
          ),
        ),
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          city.name,
                          style: const TextStyle(
                            fontSize: 14,
                            fontWeight: FontWeight.w600,
                            color: AppTheme.textPrimary,
                          ),
                        ),
                        Text(
                          '${city.country} · ${city.currency}',
                          style: const TextStyle(
                            fontSize: 11,
                            color: AppTheme.textMuted,
                          ),
                        ),
                      ],
                    ),
                  ),
                  StatusBadge(
                    city.isCached ? 'cached' : 'not fetched',
                    variant:
                        city.isCached ? BadgeVariant.green : BadgeVariant.gray,
                  ),
                ],
              ),
              if (isFetching || statusMessage != null) ...[
                const SizedBox(height: 8),
                if (isFetching)
                  const LinearProgressIndicator(
                    color: AppTheme.brand500,
                    backgroundColor: AppTheme.border,
                    minHeight: 3,
                  ),
                if (statusMessage != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 4),
                    child: Text(
                      statusMessage!,
                      style: const TextStyle(
                          fontSize: 11, color: AppTheme.textMuted),
                    ),
                  ),
              ],
              const SizedBox(height: 10),
              Row(
                children: [
                  if (city.isCached)
                    _ActionButton(
                      label: 'Refresh',
                      icon: Icons.refresh,
                      onTap: () => onFetch(true),
                      disabled: isFetching,
                    )
                  else
                    _ActionButton(
                      label: 'Fetch Data',
                      icon: Icons.cloud_download_outlined,
                      primary: true,
                      onTap: () => onFetch(false),
                      disabled: isFetching,
                    ),
                  const SizedBox(width: 8),
                  if (isSelected)
                    const StatusBadge('selected', variant: BadgeVariant.blue),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ActionButton extends StatelessWidget {
  final String label;
  final IconData icon;
  final VoidCallback? onTap;
  final bool primary;
  final bool disabled;

  const _ActionButton({
    required this.label,
    required this.icon,
    this.onTap,
    this.primary = false,
    this.disabled = false,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: disabled ? null : onTap,
      child: AnimatedOpacity(
        opacity: disabled ? 0.5 : 1.0,
        duration: const Duration(milliseconds: 150),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          decoration: BoxDecoration(
            color: primary ? AppTheme.brand600 : AppTheme.surface900,
            borderRadius: BorderRadius.circular(8),
            border: Border.all(
              color: primary ? AppTheme.brand500 : AppTheme.border,
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                icon,
                size: 13,
                color: primary ? Colors.white : AppTheme.textMuted,
              ),
              const SizedBox(width: 4),
              Text(
                label,
                style: TextStyle(
                  fontSize: 12,
                  fontWeight: FontWeight.w500,
                  color: primary ? Colors.white : AppTheme.textMuted,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
