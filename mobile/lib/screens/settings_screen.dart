// mobile/lib/screens/settings_screen.dart
// Urban Intelligence Framework v2.0.0
// App settings and configuration screen
// ignore_for_file: deprecated_member_use

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../services/providers.dart';
import '../utils/theme.dart';
import '../widgets/common_widgets.dart';

class SettingsScreen extends ConsumerStatefulWidget {
  const SettingsScreen({super.key});

  @override
  ConsumerState<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends ConsumerState<SettingsScreen> {
  bool _autoRefreshMonitoring = true;
  bool _showConfidenceIntervals = true;
  bool _enableNotifications = false;

  @override
  Widget build(BuildContext context) {
    final selectedCity = ref.watch(selectedCityProvider);
    final citiesAsync = ref.watch(citiesProvider);
    final healthAsync = ref.watch(apiHealthProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // ── General ────────────────────────────────────────────────
          _SectionCard(
            title: 'General',
            children: [
              // City selector
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Default City',
                      style:
                          TextStyle(fontSize: 13, fontWeight: FontWeight.w500),
                    ),
                    const SizedBox(height: 2),
                    const Text(
                      'Used as default across all screens',
                      style: TextStyle(fontSize: 11, color: AppTheme.textMuted),
                    ),
                    const SizedBox(height: 8),
                    citiesAsync.when(
                      loading: () => const LinearProgressIndicator(
                          color: AppTheme.brand500),
                      error: (_, __) => Text(selectedCity,
                          style: const TextStyle(color: AppTheme.textMuted)),
                      data: (cities) => DropdownButtonFormField<String>(
                        value: selectedCity,
                        dropdownColor: AppTheme.surface800,
                        decoration: const InputDecoration(
                          contentPadding: EdgeInsets.symmetric(
                              horizontal: 12, vertical: 10),
                        ),
                        items: cities
                            .map((c) => DropdownMenuItem(
                                  value: c.cityId,
                                  child: Text('${c.name} (${c.country})',
                                      style: const TextStyle(fontSize: 13)),
                                ))
                            .toList(),
                        onChanged: (v) {
                          if (v != null) {
                            ref.read(selectedCityProvider.notifier).set(v);
                          }
                        },
                      ),
                    ),
                  ],
                ),
              ),
              const Divider(),
              _Toggle(
                title: 'Auto-refresh Monitoring',
                subtitle: 'Refresh metrics every 15 seconds',
                value: _autoRefreshMonitoring,
                onChanged: (v) => setState(() => _autoRefreshMonitoring = v),
              ),
              _Toggle(
                title: 'Show Confidence Intervals',
                subtitle: 'Display CI bands on prediction results',
                value: _showConfidenceIntervals,
                onChanged: (v) => setState(() => _showConfidenceIntervals = v),
              ),
              _Toggle(
                title: 'Push Notifications',
                subtitle: 'Alerts for critical model issues',
                value: _enableNotifications,
                onChanged: (v) => setState(() => _enableNotifications = v),
              ),
            ],
          ),

          const SizedBox(height: 14),

          // ── Connection ─────────────────────────────────────────────
          _SectionCard(
            title: 'API Connection',
            children: [
              Row(
                children: [
                  const Text('Backend Status',
                      style:
                          TextStyle(fontSize: 13, fontWeight: FontWeight.w500)),
                  const Spacer(),
                  healthAsync.when(
                    loading: () => const SizedBox(
                      width: 14,
                      height: 14,
                      child: CircularProgressIndicator(
                          strokeWidth: 2, color: AppTheme.brand500),
                    ),
                    error: (_, __) =>
                        const StatusBadge('offline', variant: BadgeVariant.red),
                    data: (healthy) => StatusBadge(
                      healthy ? 'online' : 'offline',
                      variant: healthy ? BadgeVariant.green : BadgeVariant.red,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 8),
              const Text(
                'localhost:8000/api/v1',
                style: TextStyle(
                  fontSize: 12,
                  color: AppTheme.textMuted,
                  fontFamily: 'monospace',
                ),
              ),
              const SizedBox(height: 8),
              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  onPressed: () => ref.invalidate(apiHealthProvider),
                  icon: const Icon(Icons.refresh, size: 16),
                  label: const Text('Check Connection',
                      style: TextStyle(fontSize: 13)),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppTheme.brand500,
                    side: const BorderSide(color: AppTheme.brand500),
                  ),
                ),
              ),
            ],
          ),

          const SizedBox(height: 14),

          // ── About ──────────────────────────────────────────────────
          const _SectionCard(
            title: 'About',
            children: [
              MetricRow(label: 'App Version', value: 'v2.0.0'),
              Divider(height: 16),
              MetricRow(label: 'Framework', value: 'Flutter 3.x'),
              Divider(height: 16),
              MetricRow(label: 'Backend', value: 'FastAPI + Python'),
              Divider(height: 16),
              MetricRow(label: 'ML Stack', value: 'XGBoost + LightGBM'),
              Divider(height: 16),
              MetricRow(label: 'Database', value: 'DuckDB + Parquet'),
              Divider(height: 16),
              MetricRow(label: 'Author', value: 'F.J. Mercader Martínez'),
            ],
          ),

          const SizedBox(height: 14),

          // ── Reset ──────────────────────────────────────────────────
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: () => _showResetDialog(context, ref),
              icon: const Icon(Icons.restore, size: 16),
              label: const Text('Reset to Defaults',
                  style: TextStyle(fontSize: 13)),
              style: OutlinedButton.styleFrom(
                foregroundColor: AppTheme.warning,
                side: const BorderSide(color: AppTheme.warning),
              ),
            ),
          ),

          const SizedBox(height: 80),
        ],
      ),
    );
  }

  void _showResetDialog(BuildContext context, WidgetRef ref) {
    showDialog<void>(
      context: context,
      builder: (_) => AlertDialog(
        backgroundColor: AppTheme.surface800,
        title: const Text('Reset Settings', style: TextStyle(fontSize: 16)),
        content: const Text(
          'Reset all settings to their default values?',
          style: TextStyle(fontSize: 13, color: AppTheme.textMuted),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              ref.read(selectedCityProvider.notifier).set('london');
              setState(() {
                _autoRefreshMonitoring = true;
                _showConfidenceIntervals = true;
                _enableNotifications = false;
              });
              Navigator.of(context).pop();
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('Settings reset to defaults'),
                  backgroundColor: AppTheme.surface800,
                ),
              );
            },
            child: const Text('Reset', style: TextStyle(color: AppTheme.error)),
          ),
        ],
      ),
    );
  }
}

// ── Helper widgets ────────────────────────────────────────────────────────

class _SectionCard extends StatelessWidget {
  final String title;
  final List<Widget> children;

  const _SectionCard({required this.title, required this.children});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(left: 2, bottom: 8),
          child: Text(
            title.toUpperCase(),
            style: const TextStyle(
              fontSize: 10,
              fontWeight: FontWeight.w700,
              color: AppTheme.textMuted,
              letterSpacing: 1.0,
            ),
          ),
        ),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: children,
            ),
          ),
        ),
      ],
    );
  }
}

class _Toggle extends StatelessWidget {
  final String title;
  final String subtitle;
  final bool value;
  final ValueChanged<bool> onChanged;

  const _Toggle({
    required this.title,
    required this.subtitle,
    required this.value,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return SwitchListTile(
      dense: true,
      contentPadding: EdgeInsets.zero,
      title: Text(title,
          style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500)),
      subtitle: Text(subtitle,
          style: const TextStyle(fontSize: 11, color: AppTheme.textMuted)),
      value: value,
      activeColor: AppTheme.brand500,
      onChanged: onChanged,
    );
  }
}
