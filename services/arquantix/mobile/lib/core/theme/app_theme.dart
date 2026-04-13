import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../design_system/atoms/app_radius.dart';
import '../../design_system/typography.dart';

/// Thème global de l'app Arquantix News
class AppTheme {
  AppTheme._();

  static const Color _seedColor = Color(0xFF4F46E5);

  static ThemeData get light => ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: _seedColor,
          brightness: Brightness.light,
          primary: _seedColor,
        ),
        useMaterial3: true,
        fontFamily: GoogleFonts.inter().fontFamily,
        textTheme: AppTypographyTheme.textThemeStatic(),
        primaryTextTheme: AppTypographyTheme.textThemeStatic(),
        inputDecorationTheme: AppTypographyTheme.inputDecorationTheme(AppTypographyTheme.textThemeStatic()),
        filledButtonTheme: FilledButtonThemeData(
          style: FilledButton.styleFrom(
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(AppRadius.button),
            ),
          ),
        ),
        outlinedButtonTheme: OutlinedButtonThemeData(
          style: OutlinedButton.styleFrom(
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(AppRadius.button),
            ),
          ),
        ),
        textButtonTheme: TextButtonThemeData(
          style: TextButton.styleFrom(
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(AppRadius.button),
            ),
          ),
        ),
      );
}
