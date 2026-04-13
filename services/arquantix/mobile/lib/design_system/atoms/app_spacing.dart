/// Atome : échelle d'espacement du design system.
///
/// Numeric naming: the suffix is the multiplier (base unit = 4px).
class AppSpacing {
  AppSpacing._();

  static const double s0 = 0;
  static const double s1 = 4;
  static const double s2 = 8;
  static const double s3 = 12;
  static const double s4 = 16;
  static const double s5 = 20;
  static const double s6 = 24;
  static const double s7 = 28;
  static const double s8 = 32;
  static const double s10 = 40;
  static const double s12 = 48;
  static const double s16 = 64;
  static const double s20 = 80;
  static const double s24 = 96;

  // ── Legacy aliases ──

  static const double xs = s1;
  static const double sm = s2;
  static const double md = s3;
  static const double lg = s4;
  static const double xl = s5;
  static const double xxl = s6;
  static const double pageEdge = lg;

  /// Marges horizontales des modules : préférer [kModuleHorizontalMargin] (`layout/module_horizontal_margin.dart`).

  /// Figma ~40px : espace entre le bloc **titre + description** (sous-titre de page)
  /// et le **premier champ** — inscription, flows formulaire, même gabarit partout.
  static const double pageDescriptionToFirstField = s10;
}
