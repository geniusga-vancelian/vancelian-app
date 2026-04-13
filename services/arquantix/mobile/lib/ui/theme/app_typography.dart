import 'package:flutter/material.dart';

/// Typography for the floating bottom nav labels and UI components.
class AppTypography {
  AppTypography._();

  /// Nav item label: size 11, weight 500 (medium).
  static TextStyle get navLabel => const TextStyle(
        fontSize: 11,
        fontWeight: FontWeight.w500,
      );

  // ——— Transaction / list tile ———

  /// Tile title: 16sp, semi-bold.
  static TextStyle get tileTitle => const TextStyle(
        fontSize: 16,
        fontWeight: FontWeight.w600,
      );

  /// Tile subtitle: 13sp, regular/medium.
  static TextStyle get tileSubtitle => const TextStyle(
        fontSize: 13,
        fontWeight: FontWeight.w500,
      );

  /// Right primary (amount/value): 16sp, semi-bold.
  static TextStyle get tileRightPrimary => const TextStyle(
        fontSize: 16,
        fontWeight: FontWeight.w600,
      );

  /// Right secondary (%, date, status): 13sp.
  static TextStyle get tileRightSecondary => const TextStyle(
        fontSize: 13,
        fontWeight: FontWeight.w400,
      );

  // ——— Action buttons (ButtonRounded) ———

  /// Label sous le cercle : 14sp, semi-bold.
  static TextStyle get actionLabel => const TextStyle(
        fontSize: 14,
        fontWeight: FontWeight.w600,
      );
}
