// mobile/lib/main.dart
// Urban Intelligence Framework v2.0.0
// Flutter application entry point

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'screens/dashboard_screen.dart';
import 'screens/predict_screen.dart';
import 'screens/cities_screen.dart';
import 'screens/analytics_screen.dart';
import 'screens/monitoring_screen.dart';
import 'screens/settings_screen.dart';
import 'widgets/app_shell.dart';
import 'utils/theme.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();

  // Force portrait orientation
  SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.portraitDown,
  ]);

  // Dark status bar style
  SystemChrome.setSystemUIOverlayStyle(
    const SystemUiOverlayStyle(
      statusBarColor: Colors.transparent,
      statusBarIconBrightness: Brightness.light,
    ),
  );

  runApp(
    const ProviderScope(child: UrbanIntelligenceApp()),
  );
}

// ── Router ────────────────────────────────────────────────────────────────

final _router = GoRouter(
  initialLocation: '/dashboard',
  routes: [
    ShellRoute(
      builder: (context, state, child) => AppShell(child: child),
      routes: [
        GoRoute(
            path: '/dashboard', builder: (_, __) => const DashboardScreen()),
        GoRoute(path: '/predict', builder: (_, __) => const PredictScreen()),
        GoRoute(path: '/cities', builder: (_, __) => const CitiesScreen()),
        GoRoute(
            path: '/analytics', builder: (_, __) => const AnalyticsScreen()),
        GoRoute(
            path: '/monitoring', builder: (_, __) => const MonitoringScreen()),
        GoRoute(path: '/settings', builder: (_, __) => const SettingsScreen()),
      ],
    ),
  ],
);

// ── Root widget ───────────────────────────────────────────────────────────

class UrbanIntelligenceApp extends StatelessWidget {
  const UrbanIntelligenceApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'Urban Intelligence',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.dark(),
      routerConfig: _router,
    );
  }
}
