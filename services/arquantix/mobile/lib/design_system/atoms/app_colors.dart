import 'package:flutter/material.dart';

/// Atome : couleurs du design system.
///
/// Two layers:
///   1. **Designer palette** — raw color constants (base, gray, dark theme).
///   2. **Semantic aliases** — used app-wide; currently mapped to light theme.
///
/// When switching to dark mode, remap the semantic aliases to the dark-theme
/// palette values below.
class AppColors {
  AppColors._();

  // ═══════════════════════════════════════════════════════════════════════════
  // ░░░  BASE PALETTE  ░░░
  // ═══════════════════════════════════════════════════════════════════════════

  static const Color red = Color(0xFFFF4245);
  static const Color mint = Color(0xFF00DAC3);
  static const Color orange = Color(0xFFFF9230);
  static const Color yellow = Color(0xFFFFD600);
  static const Color green = Color(0xFF30D158);
  static const Color teal = Color(0xFF00D2E0);
  static const Color cyan = Color(0xFF3CD3FE);
  /// Bleu iOS / lien / état info — distinct du CTA marque (#6155F5).
  static const Color actionPrimaryBlue = Color(0xFF007AFF);

  static const Color blue = Color(0xFF0091FF);

  /// CTA principal marque — Figma Access / Button `primary` (#6155F5).
  static const Color indigo = Color(0xFF6155F5);

  /// Fond type écran permission iOS (status bar + héros) — Figma Access.
  static const Color iosChromeBackground = Color(0xFFF2F2F7);
  static const Color purple = Color(0xFFDB34F2);
  static const Color pink = Color(0xFFFF375F);
  static const Color brown = Color(0xFFB78A66);

  // ═══════════════════════════════════════════════════════════════════════════
  // ░░░  GRAY SCALE  ░░░
  // ═══════════════════════════════════════════════════════════════════════════

  static const Color black = Color(0xFF000000);
  static const Color gray = Color(0xFF8E8E93);
  static const Color gray2 = Color(0xFF636366);
  static const Color gray3 = Color(0xFF48484A);
  static const Color gray4 = Color(0xFF3A3A3C);
  static const Color gray5 = Color(0xFF2C2C2E);
  static const Color gray6 = Color(0xFF1C1C1E);
  static const Color white = Color(0xFFFFFFFF);

  // ═══════════════════════════════════════════════════════════════════════════
  // ░░░  DARK THEME PALETTE (designer spec)  ░░░
  // ═══════════════════════════════════════════════════════════════════════════

  static const Color darkBgPrimary = Color(0xFF1C1C1E);
  static const Color darkBgSecondary = Color(0xFF000000);
  static const Color darkTextPrimary = Color(0xFFFFFFFF);
  static const Color darkTextSecondary = Color(0xFF000000);
  static const Color darkTextMuted = Color(0xFF8E8E93);
  static const Color darkSeparatorOpaque = Color(0xFF48484A);
  static const Color darkSeparatorNonOpaque = Color(0x2EFFFFFF);
  static const Color darkOpacity100 = Color(0xFFFFFFFF);
  static const Color darkOpacity60 = Color(0x99EBEBF5);
  static const Color darkOpacity30 = Color(0x4DEBEBF5);
  static const Color darkOpacity18 = Color(0x2EEBEBF5);

  /// Fond glassmorphism standard — Figma rgba(60,60,67,0.6).
  /// Utilisé pour GlassBadge et AppBackButton(glassDark) sur fond photographique.
  static const Color glassOverlay = Color(0x993C3C43);

  // ═══════════════════════════════════════════════════════════════════════════
  // ░░░  SEMANTIC ALIASES (currently light theme — backward compatible)  ░░░
  // ═══════════════════════════════════════════════════════════════════════════

  static const Color textPrimary = Color(0xFF000000);
  static const Color textSecondary = Color(0xFF64748B);
  static const Color textMuted = Color(0xFF8E8E93);

  static const Color accent = indigo;
  static const Color chartLine = indigo;

  /// Anneau de progression « léger » — Figma `CircularProgress` piste.
  static const Color progressTrackLight = Color(0xFFE5E5EA);

  static const Color pageBackground = Color(0xFFF5F5F5);
  static const Color cardBackground = white;

  static const Color placeholderBg = Color(0xFFE2E8F0);
  static const Color placeholderIcon = Color(0xFF94A3B8);

  static const Color navBarBackground = white;
  static const Color navBarActivePill = Color(0xFFF1F5F9);
  static const Color navBarInactive = Color(0xFF64748B);

  static const Color userMessageBubble = Color(0xFFF5F5F5);
  static const Color chatInputBg = Color(0xFFF2F4F8);
  static const Color chatInputHint = Color(0xFF6C757D);

  static const Color border = Color(0xFFE5E7EB);
  static const Color separatorOpaque = Color(0xFFE5E7EB);
  static const Color separatorNonOpaque = Color(0x2E000000);

  static const Color errorBackground = Color(0xFFFEF2F2);
  static const Color errorText = Color(0xFF991B1B);

  // ═══════════════════════════════════════════════════════════════════════════
  // ░░░  SEMANTIC PALETTE (Figma tokens)  ░░░
  // ═══════════════════════════════════════════════════════════════════════════

  static const Color semanticNeutral = Color(0xFFAEAEB2);

  static const Color semanticActive = Color(0xFF00C3D0);
  static const Color semanticActiveLight = Color(0xFFE5F9FA);

  static const Color semanticInfo = Color(0xFF0088FF);
  static const Color semanticInfoLight = Color(0xFFE5F3FF);

  static const Color semanticWarning = Color(0xFFFF8D28);
  static const Color semanticWarningLight = Color(0xFFFFF4E9);

  static const Color semanticDanger = Color(0xFFFF383C);
  static const Color semanticDangerLight = Color(0xFFFFEBEB);

  static const Color semanticPositive = Color(0xFF34C759);
  static const Color semanticPositiveLight = Color(0xFFEBF9EE);

  static const Color semanticNegative = Color(0xFFFF2D55);
  static const Color semanticNegativeLight = Color(0xFFFFEAEE);

  static const Color accentLight = Color(0xFFEFEEFE);

  // ── Button-specific tokens (Figma module : disabled = #AEAEB2 + texte blanc) ──

  static const Color buttonDisabledBg = Color(0xFFAEAEB2);
  static const Color buttonDisabledFg = white;

  // ── Crypto asset brand colors ──

  static const Map<String, Color> cryptoAssetBrand = {
    'EUR':  Color(0xFF2196F3),
    'BTC':  Color(0xFFFF9230),
    'ETH':  Color(0xFF627EEA),
    'USDT': Color(0xFF26A17B),
    'USDC': Color(0xFF2775CA),
    'XRP':  Color(0xFF23292F),
    'SOL':  Color(0xFF9945FF),
    'BNB':  Color(0xFFF3BA2F),
    'ADA':  Color(0xFF0033AD),
    'AVAX': Color(0xFFE84142),
    'DOGE': Color(0xFFC2A633),
    'DOT':  Color(0xFFE6007A),
    'LINK': Color(0xFF2A5ADA),
    'TRX':  Color(0xFFEF0027),
  };

  static Color cryptoBrandColor(String ticker) =>
      cryptoAssetBrand[ticker.toUpperCase()] ?? textMuted;
}
