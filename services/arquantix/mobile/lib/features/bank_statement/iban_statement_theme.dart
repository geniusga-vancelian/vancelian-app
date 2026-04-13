import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Figma-aligned tokens for the bank statement document (A4 preview).
/// Keeps typography and colors deterministic for PDF parity later.
abstract final class IbanStatementTheme {
  static const Color pageBackground = Color(0xFFFFFFFF);
  static const Color headerBand = Color(0xFFF2F2F7);
  static const Color mutedLabel = Color(0xFF8E8E93);
  static const Color ink = Color(0xFF000000);
  static const Color logoInk = Color(0xFF1E1C1B);
  static const Color borderSubtle = Color(0xFFD1D1D6);
  static const Color tableHeaderRule = Color(0xFF8E8E93);

  /// A4 canvas width at ~96dpi (matches Figma export 793.701px).
  static const double a4WidthPx = 793.701;

  static const double headerPaddingH = 80;
  static const double headerPaddingTop = 80;
  static const double headerPaddingBottom = 40;
  static const double bodyPaddingH = 80;
  static const double bodyPaddingV = 40;

  static const double cardRadius = 10;
  static const double cardPadding = 20;

  static const double letterTight = -0.35;
  static const double letterMicro = -0.08;

  static TextStyle interSemiBold(double size, {double height = 1.0, Color? color}) =>
      GoogleFonts.inter(
        fontSize: size,
        height: height,
        fontWeight: FontWeight.w600,
        color: color ?? ink,
        letterSpacing: letterTight,
      );

  static TextStyle interRegular(double size, {double height = 1.0, Color? color}) =>
      GoogleFonts.inter(
        fontSize: size,
        height: height,
        fontWeight: FontWeight.w400,
        color: color ?? ink,
        letterSpacing: letterMicro,
      );

  static TextStyle interBold(double size, {double height = 1.0}) =>
      GoogleFonts.inter(
        fontSize: size,
        height: height,
        fontWeight: FontWeight.w700,
        color: ink,
        letterSpacing: letterTight,
      );
}
