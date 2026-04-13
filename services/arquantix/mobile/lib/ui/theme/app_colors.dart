import 'package:flutter/material.dart';
import '../../design_system/atoms/app_colors.dart' as DsColors;

/// Theme colors for the floating bottom nav (Apple Music–inspired) and UI components.
/// Use these instead of magic hex values.
class AppColors {
  AppColors._();

  /// Selected nav item (icon + label). Bleu du Design System (accent).
  static const Color navSelected = DsColors.AppColors.accent;

  /// Unselected nav item (icon + label). Noir primaire (texte principal).
  static const Color navUnselected = DsColors.AppColors.textPrimary;

  /// Floating bar background (white with opacity applied at use site).
  static const Color navBarBackground = Colors.white;

  /// Shadow color for bar (black with opacity applied at use site).
  static const Color navBarShadow = DsColors.AppColors.textPrimary;

  // ——— Transaction / list tile ———

  /// Primary text (titles, amounts). Black 100% from DS token.
  static const Color textPrimary = DsColors.AppColors.textPrimary;

  /// Secondary text (subtitles, meta). Grey.
  static const Color textSecondary = Color(0xFF64748B);

  /// Chevron and trailing disclosure. Light grey.
  static const Color chevronGrey = Color(0xFF94A3B8);

  /// Positive delta / gain (e.g. +1.86%).
  static const Color positive = Color(0xFF059669);

  /// Negative delta / loss (e.g. -2.10%).
  static const Color negative = Color(0xFFDC2626);

  /// Neutral secondary (when not positive/negative).
  static const Color neutral = Color(0xFF64748B);

  // ——— Action buttons (ButtonRounded) ———

  /// Fond du bouton primaire (ex. "Déposer").
  static const Color actionPrimaryBg = DsColors.AppColors.textPrimary;

  /// Icône du bouton primaire. Blanc.
  static const Color actionPrimaryIcon = Color(0xFFFFFFFF);

  /// Fond du bouton secondaire. Light grey (#E9E9EC).
  static const Color actionSecondaryBg = Color(0xFFE9E9EC);

  /// Icône du bouton secondaire.
  static const Color actionSecondaryIcon = DsColors.AppColors.textPrimary;

  /// Couleur du label sous le cercle.
  static const Color actionLabel = DsColors.AppColors.textPrimary;

  /// Fond du bouton hero primaire (pill indigo).
  static const Color actionHeroPrimaryBg = DsColors.AppColors.indigo;

  // ——— Wallet (hero + sheet) ———

  /// Début du dégradé hero (lavande).
  static const Color walletHeroStart = Color(0xFF7C7CE0);

  /// Fin du dégradé hero (violet).
  static const Color walletHeroEnd = Color(0xFF5E5EC9);

  /// Fond de la barre du haut quand collapse (blanc).
  static const Color walletAppBarBg = Colors.white;

  /// Texte / icônes de la barre quand collapse (noir).
  static const Color walletAppBarFg = DsColors.AppColors.textPrimary;

  /// Fond de la feuille blanche qui chevauche le hero.
  static const Color walletSheetBg = Colors.white;

  /// Ombre de la feuille wallet.
  static const Color walletSheetShadow = Color(0x1A000000);
}
