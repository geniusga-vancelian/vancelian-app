import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Design system typography: Inter uniquement (titres, corps, labels).
/// Single source of truth for text styles and ThemeData.textTheme.
class AppTypographyTheme {
  AppTypographyTheme._();

  static const double _displayLargeSize = 34;
  static const double _displayMediumSize = 32;
  static const double _displaySmallSize = 28;
  static const double _headlineLargeSize = 26;
  static const double _headlineMediumSize = 24;
  static const double _headlineSmallSize = 22;
  static const double _titleLargeSize = 20;
  static const double _titleMediumSize = 18;
  static const double _titleSmallSize = 16;
  static const double _bodyLargeSize = 16;
  static const double _bodyMediumSize = 14;
  static const double _bodySmallSize = 12;
  static const double _labelLargeSize = 14;
  static const double _labelMediumSize = 12;
  static const double _labelSmallSize = 11;
  static const double _amountLargeSize = 24;
  static const double _amountMediumSize = 18;
  static const double _amountSmallSize = 14;

  static const double _heightDisplay = 1.2;
  static const double _heightHeadline = 1.25;
  static const double _heightTitle = 1.3;
  static const double _heightBody = 1.5;
  static const double _heightLabel = 1.4;

  /// Letter spacing légèrement resserré pour tout le texte (Inter a un défaut un peu large).
  static const double _letterSpacingTight = -0.25;

  static TextStyle _displayInter(double size) => GoogleFonts.inter(
        fontSize: size,
        height: _heightDisplay,
        fontWeight: FontWeight.w600,
        letterSpacing: -0.6,
      );
  static TextStyle _headlineInter(double size) => GoogleFonts.inter(
        fontSize: size,
        height: _heightHeadline,
        fontWeight: FontWeight.w600,
        letterSpacing: -0.4,
      );
  static TextStyle _titleInter(double size) => GoogleFonts.inter(
        fontSize: size,
        height: _heightTitle,
        fontWeight: FontWeight.w500,
        letterSpacing: _letterSpacingTight,
      );
  static TextStyle _bodyInter(double size, [FontWeight w = FontWeight.w400]) =>
      GoogleFonts.inter(
        fontSize: size,
        height: _heightBody,
        fontWeight: w,
        letterSpacing: _letterSpacingTight,
      );
  static TextStyle _labelInter(double size, [FontWeight w = FontWeight.w500]) =>
      GoogleFonts.inter(
        fontSize: size,
        height: _heightLabel,
        fontWeight: w,
        letterSpacing: _letterSpacingTight,
      );
  static TextStyle _amountInter(double size, [FontWeight w = FontWeight.w600]) =>
      GoogleFonts.inter(
        fontSize: size,
        height: _heightTitle,
        fontWeight: w,
        letterSpacing: _letterSpacingTight,
        fontFeatures: const [FontFeature.proportionalFigures()],
      );

  /// TextTheme for ThemeData: Inter partout.
  static TextTheme textTheme(BuildContext context) {
    final base = Theme.of(context).textTheme;
    final inter = GoogleFonts.interTextTheme(base);
    return inter.copyWith(
      displayLarge: _displayInter(_displayLargeSize),
      displayMedium: _displayInter(_displayMediumSize),
      displaySmall: _displayInter(_displaySmallSize),
      headlineLarge: _headlineInter(_headlineLargeSize),
      headlineMedium: _headlineInter(_headlineMediumSize),
      headlineSmall: _headlineInter(_headlineSmallSize),
      titleLarge: _titleInter(_titleLargeSize),
      titleMedium: _titleInter(_titleMediumSize),
      titleSmall: _titleInter(_titleSmallSize),
      bodyLarge: _bodyInter(_bodyLargeSize),
      bodyMedium: _bodyInter(_bodyMediumSize),
      bodySmall: _bodyInter(_bodySmallSize),
      labelLarge: _labelInter(_labelLargeSize),
      labelMedium: _labelInter(_labelMediumSize),
      labelSmall: _labelInter(_labelSmallSize),
    );
  }

  /// TextTheme without context (e.g. for ThemeData at app level). Uses default brightness.
  static TextTheme textThemeStatic() {
    final base = ThemeData.light(useMaterial3: true).textTheme;
    final inter = GoogleFonts.interTextTheme(base);
    return inter.copyWith(
      displayLarge: _displayInter(_displayLargeSize),
      displayMedium: _displayInter(_displayMediumSize),
      displaySmall: _displayInter(_displaySmallSize),
      headlineLarge: _headlineInter(_headlineLargeSize),
      headlineMedium: _headlineInter(_headlineMediumSize),
      headlineSmall: _headlineInter(_headlineSmallSize),
      titleLarge: _titleInter(_titleLargeSize),
      titleMedium: _titleInter(_titleMediumSize),
      titleSmall: _titleInter(_titleSmallSize),
      bodyLarge: _bodyInter(_bodyLargeSize),
      bodyMedium: _bodyInter(_bodyMediumSize),
      bodySmall: _bodyInter(_bodySmallSize),
      labelLarge: _labelInter(_labelLargeSize),
      labelMedium: _labelInter(_labelMediumSize),
      labelSmall: _labelInter(_labelSmallSize),
    );
  }

  // ——— Named tokens for direct use (e.g. amount in finance widgets) ———

  static TextStyle get displayLarge => _displayInter(_displayLargeSize);
  static TextStyle get displayMedium => _displayInter(_displayMediumSize);
  static TextStyle get displaySmall => _displayInter(_displaySmallSize);
  static TextStyle get headlineLarge => _headlineInter(_headlineLargeSize);
  static TextStyle get headlineMedium => _headlineInter(_headlineMediumSize);
  static TextStyle get headlineSmall => _headlineInter(_headlineSmallSize);
  static TextStyle get titleLarge => _titleInter(_titleLargeSize);
  static TextStyle get titleMedium => _titleInter(_titleMediumSize);
  static TextStyle get titleSmall => _titleInter(_titleSmallSize);
  static TextStyle get bodyLarge => _bodyInter(_bodyLargeSize);
  static TextStyle get bodyMedium => _bodyInter(_bodyMediumSize);
  static TextStyle get bodySmall => _bodyInter(_bodySmallSize);
  static TextStyle get labelLarge => _labelInter(_labelLargeSize);
  static TextStyle get labelMedium => _labelInter(_labelMediumSize);
  static TextStyle get labelSmall => _labelInter(_labelSmallSize);

  /// Finance / amounts: Inter with tabular figures for aligned numbers.
  static TextStyle get amountLarge => _amountInter(_amountLargeSize);
  static TextStyle get amountMedium => _amountInter(_amountMediumSize);
  static TextStyle get amountSmall => _amountInter(_amountSmallSize);

  // ——— Sémantiques UI (tous Inter) ———

  /// Paragraphe : corps de texte principal (Inter).
  static TextStyle get paragraph => _bodyInter(_bodyMediumSize);
  static TextStyle get paragraphSmall => _bodyInter(_bodySmallSize);
  static TextStyle get paragraphLarge => _bodyInter(_bodyLargeSize);

  /// Input : texte saisi dans un champ (Inter).
  static TextStyle get input => _bodyInter(_bodyMediumSize);
  /// Placeholder / hint d’un champ (Inter, couleur à appliquer par le thème ou le widget).
  static TextStyle get inputHint => _bodyInter(_bodyMediumSize);
  /// Label au-dessus ou à côté d’un champ (Inter).
  static TextStyle get inputLabel => _labelInter(_labelMediumSize);

  /// Label générique (Inter). labelSmall / labelLarge sont définis plus haut (theme tokens).
  static TextStyle get label => _labelInter(_labelMediumSize);

  /// Corps de message chat / conversation (bulles, Markdown). Taille 15, line height 1.55.
  static const double _chatBodySize = 15;
  static TextStyle get chatBody =>
      _bodyInter(_chatBodySize).copyWith(height: 1.55);

  /// Montant principal du hero (layout Level1/Level2) : 34px, bold w700, même famille que display.
  static TextStyle get heroAmount =>
      _displayInter(_displayLargeSize).copyWith(fontWeight: FontWeight.w700);

  /// InputDecorationTheme pour appliquer Inter à tous les champs par défaut.
  static InputDecorationTheme inputDecorationTheme(TextTheme textTheme) {
    return InputDecorationTheme(
      hintStyle: textTheme.bodyMedium,
      labelStyle: textTheme.bodyMedium,
      floatingLabelStyle: textTheme.bodySmall,
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
      filled: true,
    );
  }
}
