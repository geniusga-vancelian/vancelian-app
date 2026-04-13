import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_spacing.dart';
import 'app_top_nav_bar.dart';
import 'layout_page_level2.dart';

// ─────────────────────────────────────────────────────────────────────────────
// LayoutPageLevel1 — Reusable Level-1 page scaffold (list / summary pages).
//
// Same anatomy as [LayoutPageLevel2]: hero (title, subtitle, actions) + scrollable
// content + pull-to-refresh (indicateur LogoLoader ; [onRefresh] optionnel).
// Use for "level 1" screens (All Crypto, Dashboard) rather than
// detail pages (Wallet detail, Instrument detail = Level 2).
//
// Every visual property is a parameter; implementation delegates to [LayoutPageLevel2].
// ─────────────────────────────────────────────────────────────────────────────

/// Reusable Level-1 page layout (list/summary).
///
/// Use for: All Crypto, Dashboard, and any page with hero + content list.
class LayoutPageLevel1 extends StatelessWidget {
  const LayoutPageLevel1({
    super.key,
    this.heroImageUrl,
    this.heroBackground,
    this.heroHeightFraction = 0.70,
    this.heroMinHeight,
    this.heroFallbackColor = const Color(0xFF0D1B2A),
    this.heroOverlay = HeroOverlayConfig.standard,
    this.title = '',
    this.titleStyle,
    this.subtitle,
    this.subtitleStyle,
    this.labels,
    this.heroActions,
    this.heroFullBleed,
    this.heroActionsBelowFullBleed,
    this.showChart = true,
    this.heroActionsAlignEnd = false,
    this.leadingType = AppTopNavBarLeading.back,
    this.onLeadingTap,
    this.navBarActions = const [],
    this.navBarForegroundColor = Colors.white,
    this.profileInitials = 'JA',
    required this.content,
    this.contentOverlapHeight = 0,
    this.moduleSpacing = AppSpacing.xl,
    this.contentPadding,
    this.footerContent,
    this.fixedBottomCta,
    this.onRefresh,
    this.backgroundColor = AppColors.pageBackground,
  });

  /// URL of the hero background image. Ignored if [heroBackground] is set.
  final String? heroImageUrl;
  final Widget? heroBackground;
  final double heroHeightFraction;
  final double? heroMinHeight;
  final Color heroFallbackColor;
  final HeroOverlayConfig heroOverlay;
  final String title;
  final TextStyle? titleStyle;
  final String? subtitle;
  final TextStyle? subtitleStyle;
  final List<LayoutPageLabel>? labels;
  final Widget? heroActions;
  final Widget? heroFullBleed;
  final Widget? heroActionsBelowFullBleed;
  final bool showChart;
  /// Voir [LayoutPageLevel2.heroActionsAlignEnd].
  final bool heroActionsAlignEnd;
  final AppTopNavBarLeading leadingType;
  final VoidCallback? onLeadingTap;
  final List<AppTopNavBarAction> navBarActions;
  final Color navBarForegroundColor;
  final String profileInitials;
  final List<Widget> content;
  final double contentOverlapHeight;
  final double moduleSpacing;
  final EdgeInsetsGeometry? contentPadding;
  final Widget? footerContent;
  final ({String label, VoidCallback onTap})? fixedBottomCta;
  /// Délégué à [LayoutPageLevel2] ; si null, pull-to-refresh avec callback vide.
  final Future<void> Function()? onRefresh;
  final Color backgroundColor;

  @override
  Widget build(BuildContext context) {
    return LayoutPageLevel2(
      heroImageUrl: heroImageUrl,
      heroBackground: heroBackground,
      heroHeightFraction: heroHeightFraction,
      heroMinHeight: heroMinHeight,
      heroFallbackColor: heroFallbackColor,
      heroOverlay: heroOverlay,
      title: title,
      titleStyle: titleStyle,
      subtitle: subtitle,
      subtitleStyle: subtitleStyle,
      labels: labels,
      heroActions: heroActions,
      heroFullBleed: heroFullBleed,
      heroActionsBelowFullBleed: heroActionsBelowFullBleed,
      showChart: showChart,
      heroActionsAlignEnd: heroActionsAlignEnd,
      leadingType: leadingType,
      onLeadingTap: onLeadingTap,
      navBarActions: navBarActions,
      navBarForegroundColor: navBarForegroundColor,
      profileInitials: profileInitials,
      content: content,
      contentOverlapHeight: contentOverlapHeight,
      moduleSpacing: moduleSpacing,
      contentPadding: contentPadding,
      footerContent: footerContent,
      fixedBottomCta: fixedBottomCta,
      onRefresh: onRefresh,
      backgroundColor: backgroundColor,
    );
  }
}
