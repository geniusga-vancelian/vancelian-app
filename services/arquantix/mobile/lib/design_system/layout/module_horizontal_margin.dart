import '../atoms/app_spacing.dart';

/// Marge horizontale **unique** pour modules d’écran, listes et carrousels (16 px = [AppSpacing.lg]).
///
/// Remplace les mélanges historiques `xl` / `lg` / [AppSpacing.pageEdge] sur les bords de contenu.
/// [DashboardLayoutConstants.moduleHorizontalMargin] doit rester alignée sur cette valeur.
const double kModuleHorizontalMargin = AppSpacing.lg;
