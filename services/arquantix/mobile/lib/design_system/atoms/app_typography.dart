import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import 'app_colors.dart';
import '../typography.dart';

/// Atome : styles de texte du design system.
///
/// Two layers:
///   1. **Designer tokens** — exact specs from the design file (page, amount,
///      section, item, body, label). Prefer these for new code.
///   2. **Legacy / Material aliases** — kept for backward-compatibility.
class AppTypography {
  AppTypography._();

  // ═══════════════════════════════════════════════════════════════════════════
  // ░░░  DESIGNER TOKENS  ░░░
  // ═══════════════════════════════════════════════════════════════════════════

  // ── Page ────────────────────────────────────────────────────────────────

  /// Page header (34px / w700 / -0.136 / lh 41)
  static TextStyle get headerPrimary => GoogleFonts.inter(
        fontSize: 34,
        fontWeight: FontWeight.w700,
        letterSpacing: -0.136,
        height: 41 / 34,
      );

  /// App bar title (20px / w600 / -0.45 / lh 25)
  static TextStyle get headerAppbar => GoogleFonts.inter(
        fontSize: 20,
        fontWeight: FontWeight.w600,
        letterSpacing: -0.45,
        height: 25 / 20,
      );

  /// Page header secondary (22px / w600 / -0.35 / lh 26)
  static TextStyle get headerSecondary => GoogleFonts.inter(
        fontSize: 22,
        fontWeight: FontWeight.w600,
        letterSpacing: -0.35,
        height: 26 / 22,
      );

  /// Figma **page/headerTertiary** : Inter Bold (700), 22px, lh 28px, letter-spacing -0.26px.
  static const double _pageHeaderTertiaryFontSize = 22;
  static const double _pageHeaderTertiaryLineHeightPx = 28;
  static const double _pageHeaderTertiaryLetterSpacingPx = -0.26;

  /// Nom d’instrument (détail page), etc. — [inherit] false pour ne pas diluer avec le thème.
  static TextStyle get headerTertiary => GoogleFonts.inter(
        fontSize: _pageHeaderTertiaryFontSize,
        fontWeight: FontWeight.w700,
        letterSpacing: _pageHeaderTertiaryLetterSpacingPx,
        height: _pageHeaderTertiaryLineHeightPx / _pageHeaderTertiaryFontSize,
      ).copyWith(inherit: false);

  /// Display (65.76px / w700 / -1.973 / lh 72)
  static TextStyle get display => GoogleFonts.inter(
        fontSize: 65.76,
        fontWeight: FontWeight.w700,
        letterSpacing: -1.973,
        height: 72 / 65.76,
      );

  /// Navbar label (11px / w600 / 0 / lh 12)
  static TextStyle get navBarLabel => GoogleFonts.inter(
        fontSize: 11,
        fontWeight: FontWeight.w600,
        letterSpacing: 0,
        height: 12 / 11,
      );

  // ── Label (11px) ───────────────────────────────────────────────────────

  /// Label regular (11px / w400 / 0.06 / lh 13)
  static TextStyle get labelRegular => GoogleFonts.inter(
        fontSize: 11,
        fontWeight: FontWeight.w400,
        letterSpacing: 0.06,
        height: 13 / 11,
      );

  /// Label emphasized (11px / w600 / 0.06 / lh 13)
  static TextStyle get labelEmphasized => GoogleFonts.inter(
        fontSize: 11,
        fontWeight: FontWeight.w600,
        letterSpacing: 0.06,
        height: 13 / 11,
      );

  /// Texte dans puces **Tags** (Figma) : même grille que [labelEmphasized], **w700** pour
  /// le rendu « emphase » sur fond blanc ; [inherit] false pour éviter la fusion thème.
  /// Tracking **0,06** — pour libellés / signes type texte (ex. « % » à côté des chiffres).
  static TextStyle get labelTagEmphasized => GoogleFonts.inter(
        fontSize: 11,
        fontWeight: FontWeight.w700,
        letterSpacing: 0.06,
        height: 13 / 11,
      ).copyWith(inherit: false);

  /// Label italic (11px / w400 / italic / 0.06 / lh 13)
  static TextStyle get labelItalic => GoogleFonts.inter(
        fontSize: 11,
        fontWeight: FontWeight.w400,
        fontStyle: FontStyle.italic,
        letterSpacing: 0.06,
        height: 13 / 11,
      );

  /// Label emphasized italic (11px / w600 / italic / 0.06 / lh 13)
  static TextStyle get labelEmphasizedItalic => GoogleFonts.inter(
        fontSize: 11,
        fontWeight: FontWeight.w600,
        fontStyle: FontStyle.italic,
        letterSpacing: 0.06,
        height: 13 / 11,
      );

  // ── Amount ─────────────────────────────────────────────────────────────

  /// Figma **amount/primary** : Inter Bold (700), 34px, line height 41px, letter-spacing **-0,4 %** du corps.
  static const double _amountPrimaryFontSize = 34;
  static const double _amountPrimaryLineHeightPx = 41;
  /// Tracking Figma : -0,4 % → `fontSize × -0,004` (px logiques Flutter).
  static const double _amountPrimaryLetterSpacingPx =
      _amountPrimaryFontSize * -0.004;

  /// Amount primary — **chiffres proportionnels** (`pnum`), comme Figma : la largeur
  /// dépend du glyphe (le « 1 » n’a pas la même chasse que le « 0 »).
  ///
  /// [inherit] à false : le style n’est pas fusionné avec [DefaultTextStyle] /
  /// thème (sinon la taille/corps du thème peut écraser l’affichage type Figma).
  static TextStyle get amountPrimary => GoogleFonts.inter(
        fontSize: _amountPrimaryFontSize,
        fontWeight: FontWeight.w700,
        letterSpacing: _amountPrimaryLetterSpacingPx,
        height: _amountPrimaryLineHeightPx / _amountPrimaryFontSize,
        fontFeatures: const [FontFeature.proportionalFigures()],
      ).copyWith(inherit: false);

  /// Amount secondary (22px / w700 / -0.26 / lh 28) — chiffres proportionnels
  static TextStyle get amountSecondary => GoogleFonts.inter(
        fontSize: 22,
        fontWeight: FontWeight.w700,
        letterSpacing: -0.26,
        height: 28 / 22,
        fontFeatures: const [FontFeature.proportionalFigures()],
      );

  /// Amount tertiary (14px / w600 / 0 / lh 16) — chiffres proportionnels
  static TextStyle get amountTertiary => GoogleFonts.inter(
        fontSize: 14,
        fontWeight: FontWeight.w600,
        letterSpacing: 0,
        height: 16 / 14,
        fontFeatures: const [FontFeature.proportionalFigures()],
      );

  // ── Article ──────────────────────────────────────────────────────────

  /// Article title — aligné sur [headerTertiary] (page/headerTertiary).
  static TextStyle get articleTitle => headerTertiary;

  // ── Section ────────────────────────────────────────────────────────────

  /// Title 1 (24px / w700 / -0.45 / lh 30) — un cran au-dessus de
  /// [sectionTitle], utilisé comme `# titre` Markdown / titre principal
  /// d'un bloc rich text quand on veut un palier supérieur à la section.
  static TextStyle get title1 => GoogleFonts.inter(
        fontSize: 24,
        fontWeight: FontWeight.w700,
        letterSpacing: -0.45,
        height: 30 / 24,
      );

  /// Section title (20px / w700 / -0.45 / lh 25)
  static TextStyle get sectionTitle => GoogleFonts.inter(
        fontSize: 20,
        fontWeight: FontWeight.w700,
        letterSpacing: -0.45,
        height: 25 / 20,
      );

  // ── Item ───────────────────────────────────────────────────────────────

  /// Item primary / bold (15px / w600 / -0.23 / lh 20)
  static TextStyle get itemPrimary => GoogleFonts.inter(
        fontSize: 15,
        fontWeight: FontWeight.w600,
        letterSpacing: -0.23,
        height: 20 / 15,
      );

  /// Item secondary / regular (15px / w400 / -0.23 / lh 20)
  static TextStyle get itemSecondary => GoogleFonts.inter(
        fontSize: 15,
        fontWeight: FontWeight.w400,
        letterSpacing: -0.23,
        height: 20 / 15,
      );

  /// Figma **subtitle/Emphasized** — label colonne gauche (module Vault KeyInformation / [TableInformationModule]).
  /// Même grille que [itemPrimary] : 15px / w600 / -0.23 / lh 20.
  static TextStyle get subtitleEmphasized => itemPrimary;

  /// Figma **subtitle/Regular** — valeur colonne droite (module Vault KeyInformation / [TableInformationModule]).
  /// Même grille que [itemSecondary] : 15px / w400 / -0.23 / lh 20.
  static TextStyle get subtitleRegular => itemSecondary;

  /// Item supporting (14px / w400 / -0.08 / lh 18)
  static TextStyle get itemSupporting => GoogleFonts.inter(
        fontSize: 14,
        fontWeight: FontWeight.w400,
        letterSpacing: -0.08,
        height: 18 / 14,
      );

  /// Figma **item/supportingBD** : Inter **w600**, 14px, lh 18, letter-spacing **-0,08** px.
  static TextStyle get itemSupportingBd => GoogleFonts.inter(
        fontSize: 14,
        fontWeight: FontWeight.w600,
        letterSpacing: -0.08,
        height: 18 / 14,
      );

  /// Alias sémantique Figma : même style que [itemSupportingBd].
  static TextStyle get supportingBd => itemSupportingBd;

  // ── Button ─────────────────────────────────────────────────────────────

  /// Figma **button/Emphasized** : Inter Semi Bold (600), 16px, lh 21px, letter-spacing -0.31px.
  /// Liens du module Vault [SimpleMarkdownContentModule] (rangée dédiée + liens inline Markdown).
  static TextStyle get buttonEmphasized => GoogleFonts.inter(
        fontSize: 16,
        fontWeight: FontWeight.w600,
        letterSpacing: -0.31,
        height: 21 / 16,
      );

  /// Même spec que **item/supportingBD**, pour **puces performance** : chiffres proportionnels
  /// (`pnum`) et [inherit] false (évite fusion thème / tabular implicite).
  static TextStyle get supportingBdPerformanceChip =>
      itemSupportingBd.copyWith(
        inherit: false,
        fontFeatures: const [FontFeature.proportionalFigures()],
      );

  // ── Body (17px) ────────────────────────────────────────────────────────

  /// Body regular (17px / w400 / -0.43 / lh 22)
  static TextStyle get bodyRegular => GoogleFonts.inter(
        fontSize: 17,
        fontWeight: FontWeight.w400,
        letterSpacing: -0.43,
        height: 22 / 17,
      );

  /// Body emphasized (17px / w600 / -0.43 / lh 22)
  static TextStyle get bodyEmphasized => GoogleFonts.inter(
        fontSize: 17,
        fontWeight: FontWeight.w600,
        letterSpacing: -0.43,
        height: 22 / 17,
      );

  /// Body italic (17px / w400 / italic / -0.43 / lh 22)
  static TextStyle get bodyItalic => GoogleFonts.inter(
        fontSize: 17,
        fontWeight: FontWeight.w400,
        fontStyle: FontStyle.italic,
        letterSpacing: -0.43,
        height: 22 / 17,
      );

  /// Body emphasized italic (17px / w600 / italic / -0.43 / lh 22)
  static TextStyle get bodyEmphasizedItalic => GoogleFonts.inter(
        fontSize: 17,
        fontWeight: FontWeight.w600,
        fontStyle: FontStyle.italic,
        letterSpacing: -0.43,
        height: 22 / 17,
      );

  // ── Body SM (13px) ─────────────────────────────────────────────────────

  /// Body SM regular (13px / w400 / -0.08 / lh 18)
  static TextStyle get bodySmRegular => GoogleFonts.inter(
        fontSize: 13,
        fontWeight: FontWeight.w400,
        letterSpacing: -0.08,
        height: 18 / 13,
      );

  /// Body SM emphasized (13px / w600 / -0.08 / lh 18)
  static TextStyle get bodySmEmphasized => GoogleFonts.inter(
        fontSize: 13,
        fontWeight: FontWeight.w600,
        letterSpacing: -0.08,
        height: 18 / 13,
      );

  /// Body SM italic (13px / w400 / italic / -0.08 / lh 18)
  static TextStyle get bodySmItalic => GoogleFonts.inter(
        fontSize: 13,
        fontWeight: FontWeight.w400,
        fontStyle: FontStyle.italic,
        letterSpacing: -0.08,
        height: 18 / 13,
      );

  /// Body SM emphasized italic (13px / w600 / italic / -0.08 / lh 18)
  static TextStyle get bodySmEmphasizedItalic => GoogleFonts.inter(
        fontSize: 13,
        fontWeight: FontWeight.w600,
        fontStyle: FontStyle.italic,
        letterSpacing: -0.08,
        height: 18 / 13,
      );

  // ═══════════════════════════════════════════════════════════════════════════
  // ░░░  LEGACY / BACKWARD-COMPATIBLE ALIASES  ░░░
  // ═══════════════════════════════════════════════════════════════════════════

  /// Titre de page legacy — maps to [headerPrimary]
  static TextStyle get pageTitle => headerPrimary.copyWith(
        color: AppColors.textPrimary,
        fontWeight: FontWeight.w800,
      );

  /// Titre app bar legacy
  static TextStyle get appBarTitle => headerAppbar;

  /// Titre de section secondaire (~17px)
  static TextStyle get sectionTitle2 => sectionTitle.copyWith(fontSize: 17);

  /// Titre 2 (16px / w600)
  static TextStyle get title2 => GoogleFonts.inter(
        fontSize: 16,
        fontWeight: FontWeight.w600,
        letterSpacing: -0.23,
        height: 20 / 16,
      );

  /// Titre de modale / bottom sheet
  static TextStyle get modalTitle => sectionTitle;

  /// Titre d'accueil / bienvenue
  static TextStyle get welcomeTitle => sectionTitle.copyWith(fontSize: 22);

  /// Titre de carte à la une
  static TextStyle get featuredCardTitle => titleMedium.copyWith(
        color: AppColors.textPrimary,
        height: 1.3,
      );

  /// Titre de carte news (liste)
  static TextStyle get newsCardTitle => titleSmall.copyWith(
        color: AppColors.textPrimary,
        height: 1.3,
      );

  /// Meta (temps de lecture, etc.)
  static TextStyle get meta => itemSupporting.copyWith(
        color: AppColors.textSecondary,
      );

  /// Label des chips / tabs
  static TextStyle chipLabel({required bool selected}) =>
      labelEmphasized.copyWith(
        color: selected ? Colors.white : AppColors.textPrimary,
      );

  // ── Material Design theme passthrough ──

  static TextStyle get displayLarge => AppTypographyTheme.displayLarge;
  static TextStyle get displayMedium => AppTypographyTheme.displayMedium;
  static TextStyle get displaySmall => AppTypographyTheme.displaySmall;
  static TextStyle get headlineLarge => AppTypographyTheme.headlineLarge;
  static TextStyle get headlineMedium => AppTypographyTheme.headlineMedium;
  static TextStyle get headlineSmall => AppTypographyTheme.headlineSmall;
  static TextStyle get titleLarge => AppTypographyTheme.titleLarge;
  static TextStyle get titleMedium => AppTypographyTheme.titleMedium;
  static TextStyle get titleSmall => AppTypographyTheme.titleSmall;
  static TextStyle get bodyLarge => AppTypographyTheme.bodyLarge;
  static TextStyle get bodyMedium => AppTypographyTheme.bodyMedium;
  static TextStyle get bodySmall => AppTypographyTheme.bodySmall;
  static TextStyle get labelLarge => AppTypographyTheme.labelLarge;
  static TextStyle get labelMedium => AppTypographyTheme.labelMedium;
  static TextStyle get labelSmall => AppTypographyTheme.labelSmall;

  // ── Finance / amounts (legacy) ──

  static TextStyle get amountLarge => amountPrimary;
  static TextStyle get amountMedium => amountSecondary;
  static TextStyle get amountSmall => amountTertiary;
  static TextStyle get heroAmount => amountPrimary;

  // ── Sémantiques UI (legacy) ──

  static TextStyle get paragraph => bodyRegular;
  static TextStyle get paragraphSmall => bodySmRegular;
  static TextStyle get paragraphLarge => bodyRegular;

  static TextStyle get input => bodyRegular;
  static TextStyle get inputHint => bodyRegular;
  static TextStyle get inputLabel => labelRegular;

  static TextStyle get label => labelRegular;

  static TextStyle get chatBody => itemPrimary.copyWith(
        height: 1.55,
        color: AppColors.textPrimary,
      );
}
