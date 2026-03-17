// mobile/lib/utils/theme.dart
// Urban Intelligence Framework v2.0.0
// Material 3 dark theme definition — Inter font loaded via google_fonts

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

class AppTheme {
  // Brand colours matching the web dashboard
  static const Color brand500 = Color(0xFF3B82F6);
  static const Color brand600 = Color(0xFF2563EB);
  static const Color surface800 = Color(0xFF1E293B);
  static const Color surface900 = Color(0xFF0F172A);
  static const Color surfaceCard = Color(0xFF1E293B);
  static const Color border = Color(0xFF334155);
  static const Color textPrimary = Color(0xFFF1F5F9);
  static const Color textMuted = Color(0xFF64748B);
  static const Color success = Color(0xFF10B981);
  static const Color warning = Color(0xFFF59E0B);
  static const Color error = Color(0xFFEF4444);

  static ThemeData dark() {
    final base = ThemeData.dark(useMaterial3: true);

    // Use Google Fonts Inter as the base text theme
    final interTextTheme = GoogleFonts.interTextTheme(base.textTheme).apply(
      bodyColor: textPrimary,
      displayColor: textPrimary,
    );

    return base.copyWith(
      scaffoldBackgroundColor: surface900,
      textTheme: interTextTheme,
      colorScheme: const ColorScheme.dark(
        primary: brand500,
        secondary: brand600,
        surface: surface800,
        error: error,
        onPrimary: Colors.white,
        onSecondary: Colors.white,
        onSurface: textPrimary,
      ),
      appBarTheme: AppBarTheme(
        backgroundColor: surface900,
        foregroundColor: textPrimary,
        elevation: 0,
        titleTextStyle: GoogleFonts.inter(
          fontSize: 17,
          fontWeight: FontWeight.w600,
          color: textPrimary,
        ),
      ),
      cardTheme: CardThemeData(
        color: surfaceCard,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: const BorderSide(color: border, width: 0.5),
        ),
        margin: EdgeInsets.zero,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: surface900,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: border),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: brand500, width: 2),
        ),
        labelStyle: GoogleFonts.inter(color: textMuted),
        hintStyle: GoogleFonts.inter(color: textMuted),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: brand600,
          foregroundColor: Colors.white,
          minimumSize: const Size.fromHeight(46),
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
          textStyle: GoogleFonts.inter(fontWeight: FontWeight.w600),
        ),
      ),
      dividerTheme: const DividerThemeData(color: border, thickness: 0.5),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: surface800,
        indicatorColor: brand600.withAlpha((0.2 * 255).round()),
        iconTheme: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return const IconThemeData(color: brand500);
          }
          return const IconThemeData(color: textMuted);
        }),
        labelTextStyle: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return GoogleFonts.inter(
                color: brand500, fontSize: 11, fontWeight: FontWeight.w500);
          }
          return GoogleFonts.inter(color: textMuted, fontSize: 11);
        }),
      ),
    );
  }
}
