import 'package:flutter/material.dart';

/// Theme data for the floating bottom nav demo.
/// Material 3; nav-specific colors/typography live in app_colors.dart and app_typography.dart.
class AppTheme {
  AppTheme._();

  static ThemeData get light => ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFFFF3B30)),
        brightness: Brightness.light,
      );
}
