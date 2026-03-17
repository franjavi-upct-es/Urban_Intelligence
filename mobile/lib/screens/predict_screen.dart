// mobile/lib/screens/predict_screen.dart
// Urban Intelligence Framework v2.0.0
// Price prediction form screen for the mobile app
// ignore_for_file: deprecated_member_use

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/prediction.dart';
import '../services/providers.dart';
import '../services/api_service.dart';
import '../utils/theme.dart';
import '../widgets/common_widgets.dart';

// ── Room type options ─────────────────────────────────────────────────────

const _roomTypes = [
  'Entire home/apt',
  'Private room',
  'Shared room',
  'Hotel room',
];

// ── Screen ────────────────────────────────────────────────────────────────

class PredictScreen extends ConsumerStatefulWidget {
  const PredictScreen({super.key});

  @override
  ConsumerState<PredictScreen> createState() => _PredictScreenState();
}

class _PredictScreenState extends ConsumerState<PredictScreen> {
  bool _isLoading = false;
  String? _errorMessage;

  // Form field controllers
  late TextEditingController _neighbourhoodCtrl;
  late TextEditingController _bedroomsCtrl;
  late TextEditingController _bedsCtrl;
  late TextEditingController _bathroomsCtrl;
  late TextEditingController _accommodatesCtrl;
  late TextEditingController _amenityCtrl;
  late TextEditingController _reviewCtrl;

  @override
  void initState() {
    super.initState();
    final req = ref.read(predictionRequestProvider);
    _neighbourhoodCtrl = TextEditingController(text: req.neighbourhood ?? '');
    _bedroomsCtrl = TextEditingController(text: '${req.bedrooms}');
    _bedsCtrl = TextEditingController(text: '${req.beds}');
    _bathroomsCtrl = TextEditingController(text: '${req.bathrooms}');
    _accommodatesCtrl = TextEditingController(text: '${req.accommodates}');
    _amenityCtrl = TextEditingController(text: '${req.amenityCount}');
    _reviewCtrl = TextEditingController(text: '${req.reviewScoresRating}');
  }

  @override
  void dispose() {
    for (final c in [
      _neighbourhoodCtrl,
      _bedroomsCtrl,
      _bedsCtrl,
      _bathroomsCtrl,
      _accommodatesCtrl,
      _amenityCtrl,
      _reviewCtrl,
    ]) {
      c.dispose();
    }
    super.dispose();
  }

  // ── Build form from current state ─────────────────────────────────────

  PredictionRequest _buildRequest() {
    final base = ref.read(predictionRequestProvider);
    return base.copyWith(
      neighbourhood:
          _neighbourhoodCtrl.text.isEmpty ? 'unknown' : _neighbourhoodCtrl.text,
      bedrooms: int.tryParse(_bedroomsCtrl.text) ?? base.bedrooms,
      beds: int.tryParse(_bedsCtrl.text) ?? base.beds,
      bathrooms: double.tryParse(_bathroomsCtrl.text) ?? base.bathrooms,
      accommodates: int.tryParse(_accommodatesCtrl.text) ?? base.accommodates,
      amenityCount: int.tryParse(_amenityCtrl.text) ?? base.amenityCount,
      reviewScoresRating:
          double.tryParse(_reviewCtrl.text) ?? base.reviewScoresRating,
    );
  }

  Future<void> _predict() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });
    try {
      final api = ref.read(apiServiceProvider);
      final result = await api.predictSingle(_buildRequest());
      ref.read(latestPredictionProvider.notifier).state = result;
      ref.invalidate(predictionHistoryProvider);
    } on ApiException catch (e) {
      setState(() => _errorMessage = e.message);
    } catch (e) {
      setState(() => _errorMessage = e.toString());
    } finally {
      setState(() => _isLoading = false);
    }
  }

  // ── UI ────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final req = ref.watch(predictionRequestProvider);
    final result = ref.watch(latestPredictionProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Price Prediction'),
        actions: [
          TextButton(
            onPressed: () {
              ref.read(latestPredictionProvider.notifier).state = null;
              setState(() => _errorMessage = null);
            },
            child: const Text('Reset',
                style: TextStyle(color: AppTheme.textMuted)),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ── Result card (shown when prediction is ready) ──────────
            if (result != null) _ResultCard(result: result),
            if (result != null) const SizedBox(height: 16),

            // ── Error banner ──────────────────────────────────────────
            if (_errorMessage != null) ...[
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppTheme.error.withAlpha((0.1 * 255).round()),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                      color: AppTheme.error.withAlpha((0.4 * 255).round())),
                ),
                child: Row(
                  children: [
                    const Icon(Icons.error_outline,
                        color: AppTheme.error, size: 16),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(_errorMessage!,
                          style: const TextStyle(
                              color: AppTheme.error, fontSize: 13)),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 12),
            ],

            // ── Form ──────────────────────────────────────────────────
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const SectionTitle('Listing Details'),
                    const SizedBox(height: 14),

                    // City selector
                    _buildLabel('City'),
                    _CitySelector(
                      currentValue: req.cityId,
                      onChanged: (v) => ref
                          .read(predictionRequestProvider.notifier)
                          .state = req.copyWith(cityId: v),
                    ),
                    const SizedBox(height: 12),

                    // Room type
                    _buildLabel('Room Type'),
                    DropdownButtonFormField<String>(
                      value: req.roomType,
                      dropdownColor: AppTheme.surface800,
                      decoration: const InputDecoration(
                        contentPadding:
                            EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                      ),
                      items: _roomTypes
                          .map((t) => DropdownMenuItem(
                              value: t,
                              child: Text(t,
                                  style: const TextStyle(fontSize: 13))))
                          .toList(),
                      onChanged: (v) {
                        if (v != null) {
                          ref.read(predictionRequestProvider.notifier).state =
                              req.copyWith(roomType: v);
                        }
                      },
                    ),
                    const SizedBox(height: 12),

                    // Neighbourhood
                    _buildLabel('Neighbourhood'),
                    TextField(
                      controller: _neighbourhoodCtrl,
                      decoration: const InputDecoration(
                        hintText: 'e.g. Westminster',
                        contentPadding:
                            EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                      ),
                      style: const TextStyle(fontSize: 13),
                    ),
                    const SizedBox(height: 12),

                    // Capacity row
                    Row(children: [
                      Expanded(
                          child:
                              _NumberField('Accommodates', _accommodatesCtrl)),
                      const SizedBox(width: 8),
                      Expanded(child: _NumberField('Bedrooms', _bedroomsCtrl)),
                    ]),
                    const SizedBox(height: 8),
                    Row(children: [
                      Expanded(child: _NumberField('Beds', _bedsCtrl)),
                      const SizedBox(width: 8),
                      Expanded(
                          child: _NumberField('Bathrooms', _bathroomsCtrl)),
                    ]),
                    const SizedBox(height: 12),

                    // Amenity + review
                    Row(children: [
                      Expanded(
                          child: _NumberField('Amenity Count', _amenityCtrl)),
                      const SizedBox(width: 8),
                      Expanded(
                          child: _NumberField('Review Score', _reviewCtrl)),
                    ]),
                    const SizedBox(height: 12),

                    // Toggles
                    Row(children: [
                      Expanded(
                        child: SwitchListTile(
                          dense: true,
                          contentPadding: EdgeInsets.zero,
                          title: const Text('Superhost',
                              style: TextStyle(fontSize: 13)),
                          value: req.hostIsSuperhost,
                          activeColor: AppTheme.brand500,
                          onChanged: (v) => ref
                              .read(predictionRequestProvider.notifier)
                              .state = req.copyWith(hostIsSuperhost: v),
                        ),
                      ),
                      Expanded(
                        child: SwitchListTile(
                          dense: true,
                          contentPadding: EdgeInsets.zero,
                          title: const Text('Instant Book',
                              style: TextStyle(fontSize: 13)),
                          value: req.instantBookable,
                          activeColor: AppTheme.brand500,
                          onChanged: (v) => ref
                              .read(predictionRequestProvider.notifier)
                              .state = req.copyWith(instantBookable: v),
                        ),
                      ),
                    ]),
                  ],
                ),
              ),
            ),

            const SizedBox(height: 16),

            // ── Submit button ─────────────────────────────────────────
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: _isLoading ? null : _predict,
                icon: _isLoading
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white,
                        ),
                      )
                    : const Icon(Icons.trending_up, size: 18),
                label: Text(_isLoading ? 'Predicting…' : 'Predict Price'),
              ),
            ),

            const SizedBox(height: 80),
          ],
        ),
      ),
    );
  }

  Widget _buildLabel(String text) => Padding(
        padding: const EdgeInsets.only(bottom: 6),
        child: Text(text,
            style: const TextStyle(fontSize: 12, color: AppTheme.textMuted)),
      );
}

// ── Sub-widgets ───────────────────────────────────────────────────────────

class _NumberField extends StatelessWidget {
  final String label;
  final TextEditingController controller;

  const _NumberField(this.label, this.controller);

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label,
            style: const TextStyle(fontSize: 12, color: AppTheme.textMuted)),
        const SizedBox(height: 4),
        TextField(
          controller: controller,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          decoration: const InputDecoration(
            contentPadding: EdgeInsets.symmetric(horizontal: 10, vertical: 10),
          ),
          style: const TextStyle(fontSize: 13),
        ),
      ],
    );
  }
}

class _CitySelector extends ConsumerWidget {
  final String currentValue;
  final ValueChanged<String> onChanged;

  const _CitySelector({required this.currentValue, required this.onChanged});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final citiesAsync = ref.watch(citiesProvider);
    return citiesAsync.when(
      loading: () => const LinearProgressIndicator(color: AppTheme.brand500),
      error: (_, __) => TextField(
        readOnly: true,
        controller: TextEditingController(text: currentValue),
        decoration: const InputDecoration(
          contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        ),
      ),
      data: (cities) => DropdownButtonFormField<String>(
        value: currentValue,
        dropdownColor: AppTheme.surface800,
        decoration: const InputDecoration(
          contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        ),
        items: cities
            .map((c) => DropdownMenuItem(
                  value: c.cityId,
                  child: Text('${c.name} (${c.country})',
                      style: const TextStyle(fontSize: 13)),
                ))
            .toList(),
        onChanged: (v) {
          if (v != null) onChanged(v);
        },
      ),
    );
  }
}

class _ResultCard extends StatelessWidget {
  final dynamic result;
  const _ResultCard({required this.result});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            AppTheme.brand600.withAlpha((0.2 * 255).round()),
            AppTheme.surface800
          ],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(12),
        border:
            Border.all(color: AppTheme.brand500.withAlpha((0.4 * 255).round())),
      ),
      child: Column(
        children: [
          const Text(
            'PREDICTED NIGHTLY PRICE',
            style: TextStyle(
                fontSize: 10, letterSpacing: 1, color: AppTheme.textMuted),
          ),
          const SizedBox(height: 6),
          Text(
            '\$${result.predictedPrice.toStringAsFixed(2)}',
            style: const TextStyle(
              fontSize: 36,
              fontWeight: FontWeight.w800,
              color: AppTheme.brand500,
              fontFamily: 'Inter',
            ),
          ),
          Text(
            'CI: \$${result.confidenceInterval.lower.toStringAsFixed(0)} – \$${result.confidenceInterval.upper.toStringAsFixed(0)}',
            style: const TextStyle(fontSize: 12, color: AppTheme.textMuted),
          ),
          const SizedBox(height: 8),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              _Chip('${result.latencyMs.toStringAsFixed(1)}ms'),
              const SizedBox(width: 8),
              _Chip('v${result.modelVersion}'),
              const SizedBox(width: 8),
              _Chip(result.currency),
            ],
          ),
        ],
      ),
    );
  }
}

class _Chip extends StatelessWidget {
  final String label;
  const _Chip(this.label);

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(
          color: AppTheme.surface800,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: AppTheme.border),
        ),
        child: Text(label,
            style: const TextStyle(fontSize: 10, color: AppTheme.textMuted)),
      );
}
