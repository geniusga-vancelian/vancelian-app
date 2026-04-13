import 'dart:math' as math;
import 'dart:ui';

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../../features/wallet/widgets/dashboard_scroll_template.dart';
import '../atoms/app_colors.dart';
import '../atoms/dashboard_header_gradient.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';
import 'app_top_nav_bar.dart';
import 'glass_badge.dart';

// ─────────────────────────────────────────────────────────────────────────────
// LayoutPageLevel2 — Reusable Level-2 detail page scaffold.
//
// Anatomy (top → bottom):
//   ┌──────────────── hero background (dégradé [DashboardHeaderGradient] ou widget) ─┐
//   │  Transparent AppTopNavBar (back button, optional actions)           │
//   │                                                                     │
//   │  [labels]           ← optional chips                                │
//   │  TITLE              ← required, centered, white                     │
//   │  subtitle           ← optional, centered, white                     │
//   │  [heroActions]         ← optional (sous-titre), 8px sous le montant  │
//   │  [heroFullBleed]       ← optional full-width (e.g. line chart)        │
//   │  [heroActionsBelowFullBleed] ← optional (e.g. boutons), padded       │
//   └─────────────────────────────────────────────────────────────────────┘
//   ┌─ content (overlaps hero by [contentOverlapHeight]) ─────────────────┐
//   │  modules…                                                           │
//   │  [footer]                                                           │
//   └─────────────────────────────────────────────────────────────────────┘
//   [fixed bottom CTA]  ← optional
//
// Every visual property is a parameter. No magic values.
// ─────────────────────────────────────────────────────────────────────────────

/// Label chip displayed above the title in the hero area.
class LayoutPageLabel {
  const LayoutPageLabel({
    required this.text,
    this.backgroundColor,
    this.textColor,
  });

  final String text;
  final Color? backgroundColor;
  final Color? textColor;
}

/// Configuration for the hero background overlay (dark tint + gradient).
class HeroOverlayConfig {
  const HeroOverlayConfig({
    this.tintColor = Colors.black,
    this.tintOpacity = 0.20,
    this.gradientBegin = Alignment.bottomLeft,
    this.gradientEnd = Alignment.topRight,
    this.gradientStartOpacity = 0.60,
    this.gradientEndOpacity = 0.20,
  });

  final Color tintColor;
  final double tintOpacity;
  final AlignmentGeometry gradientBegin;
  final AlignmentGeometry gradientEnd;
  final double gradientStartOpacity;
  final double gradientEndOpacity;

  static const HeroOverlayConfig standard = HeroOverlayConfig();
  static const HeroOverlayConfig none = HeroOverlayConfig(
    tintOpacity: 0,
    gradientStartOpacity: 0,
    gradientEndOpacity: 0,
  );
}

/// Reusable Level-2 detail page layout.
///
/// Provides a hero background with transparent nav bar, centered title area,
/// and scrollable content that overlaps the hero image.
///
/// Use for: crypto bundle detail, instrument detail, product detail, etc.
class LayoutPageLevel2 extends StatefulWidget {
  /// Espace vertical entre le montant principal (subtitle) et le sous-titre (heroActions).
  static const double _gapAmountToSubtitle = 8;

  /// Marge verticale autour du hero full-bleed (ex. line chart), référence Wallet details.
  static const double _heroFullBleedVerticalMargin = AppSpacing.lg;

  const LayoutPageLevel2({
    super.key,
    // ── Hero ──
    this.heroImageUrl,
    this.heroBackground,
    this.heroHeightFraction = 0.70,
    this.heroMinHeight,
    this.heroFallbackColor = const Color(0xFF0D1B2A),
    this.heroOverlay = HeroOverlayConfig.standard,
    // ── Title area ──
    this.title = '',
    this.titleStyle,
    this.subtitle,
    this.subtitleStyle,
    this.labels,
    this.heroActions,
    this.heroFullBleed,
    this.heroActionsBelowFullBleed,
    this.showChart = true,
    /// Si true : [heroActions] est poussé en bas du hero (comme la courbe / le bloc bas).
    this.heroActionsAlignEnd = false,
    // ── Nav bar ──
    this.leadingType = AppTopNavBarLeading.back,
    this.onLeadingTap,
    this.navBarActions = const [],
    this.navBarForegroundColor = Colors.white,
    this.profileInitials = 'JA',
    // ── Content ──
    required this.content,
    this.contentOverlapHeight = 0,
    this.moduleSpacing = AppSpacing.xl,
    this.contentPadding,
    this.footerContent,
    // ── Bottom CTA ──
    this.fixedBottomCta,
    // ── Behavior ──
    this.onRefresh,
    this.backgroundColor = AppColors.pageBackground,
  });

  // ── Hero ──

  /// URL of the hero background image. Ignored if [heroBackground] is set.
  final String? heroImageUrl;

  /// Fully custom hero background widget (replaces image + overlay).
  final Widget? heroBackground;

  /// Fraction of screen height occupied by the hero (0.0–1.0).
  final double heroHeightFraction;

  /// Absolute minimum pixel height for the hero area.
  /// When set, the hero will never be smaller than this value
  /// even if [heroHeightFraction] * screen yields less.
  final double? heroMinHeight;

  /// Solid color shown when no image is available.
  final Color heroFallbackColor;

  /// Dark overlay applied on top of the hero image.
  final HeroOverlayConfig heroOverlay;

  // ── Title area ──

  /// Page title displayed centered in the hero.
  final String title;

  /// Override style for the title.
  final TextStyle? titleStyle;

  /// Subtitle displayed below the title.
  final String? subtitle;

  /// Override style for the subtitle.
  final TextStyle? subtitleStyle;

  /// Small chips displayed above the title.
  final List<LayoutPageLabel>? labels;

  /// Widget below the subtitle (sous-titre, ex. période ou "1 crypto-actif").
  /// Ne pas ajouter de Padding/margin dans ce widget : le layout gère tout l'espacement.
  final Widget? heroActions;

  /// Optional full-width widget below [heroActions] (e.g. line chart edge-to-edge).
  final Widget? heroFullBleed;

  /// Optional widget below [heroFullBleed] (e.g. action buttons Acheter/Vendre), padded.
  final Widget? heroActionsBelowFullBleed;

  /// When false, [heroFullBleed] is not displayed and the header layout adapts (balance position).
  final bool showChart;

  /// Ancrage bas du bloc [heroActions] dans la zone hero (ex. activation pré-dépôt).
  final bool heroActionsAlignEnd;

  // ── Nav bar ──

  final AppTopNavBarLeading leadingType;
  final VoidCallback? onLeadingTap;
  final List<AppTopNavBarAction> navBarActions;
  final Color navBarForegroundColor;
  final String profileInitials;

  // ── Content ──

  /// Scrollable module widgets.
  final List<Widget> content;

  /// Pixels the first content module overlaps the hero.
  final double contentOverlapHeight;

  /// Vertical gap between content modules.
  final double moduleSpacing;

  /// Optional horizontal padding around content modules.
  final EdgeInsetsGeometry? contentPadding;

  /// Optional footer at the very bottom of the scroll.
  final Widget? footerContent;

  // ── Bottom CTA ──

  /// Fixed bottom call-to-action. If null, no CTA bar is shown.
  final ({String label, VoidCallback onTap})? fixedBottomCta;

  // ── Behavior ──

  /// Pull-to-refresh. Si null, un rafraîchissement vide est utilisé (geste + indicateur toujours actifs).
  final Future<void> Function()? onRefresh;

  /// Page background color.
  final Color backgroundColor;

  @override
  State<LayoutPageLevel2> createState() => _LayoutPageLevel2State();
}

class _LayoutPageLevel2State extends State<LayoutPageLevel2> {
  final ScrollController _scrollController = ScrollController();
  double _navTitleOpacity = 0;
  double _heroHeaderHeight = 0;

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
  }

  @override
  void dispose() {
    _scrollController.removeListener(_onScroll);
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    final offset = _scrollController.hasClients ? _scrollController.offset : 0.0;
    // Transition starts at 30% of hero header, completes over the next 20%.
    final start = _heroHeaderHeight * 0.30;
    final range = _heroHeaderHeight * 0.20;
    final next = range > 0
        ? ((offset - start) / range).clamp(0.0, 1.0)
        : 0.0;
    if ((next - _navTitleOpacity).abs() > 0.02) {
      setState(() => _navTitleOpacity = next);
    }
  }

  // ─────────────── Build ───────────────

  @override
  Widget build(BuildContext context) {
    final screenHeight = MediaQuery.sizeOf(context).height;
    final topPadding = MediaQuery.paddingOf(context).top;
    final navBarHeight = topPadding + kToolbarHeight;

    // Estimate minimum hero height so content never overflows.
    final hasTitle = widget.title.trim().isNotEmpty;
    final hasSubtitle = (widget.subtitle ?? '').trim().isNotEmpty;
    final hasLabels = widget.labels != null && widget.labels!.isNotEmpty;
    final hasActions = widget.heroActions != null;
    final hasFullBleed = widget.heroFullBleed != null;
    final hasActionsBelow = widget.heroActionsBelowFullBleed != null;
    final showChartArea = hasFullBleed && widget.showChart;
    final alignActionsEnd = widget.heroActionsAlignEnd &&
        widget.heroActions != null &&
        !showChartArea;

    double contentEstimate = 0;
    if (hasLabels) contentEstimate += 30 + AppSpacing.md;
    if (hasTitle) contentEstimate += 42;
    if (hasSubtitle) contentEstimate += AppSpacing.sm + 22;
    if (showChartArea) contentEstimate += AppSpacing.lg + 80;
    if (hasActions) {
      contentEstimate += LayoutPageLevel2._gapAmountToSubtitle +
          (alignActionsEnd ? 320 : 40);
    }
    if (hasActionsBelow) contentEstimate += AppSpacing.lg + 70;

    final safeMinHeight = navBarHeight
        + AppSpacing.md
        + contentEstimate
        + AppSpacing.xl
        + widget.contentOverlapHeight
        + AppSpacing.pageEdge;

    final fractionHeight = screenHeight * widget.heroHeightFraction;
    final heroBackgroundHeight = math.max(fractionHeight,
        widget.heroMinHeight ?? safeMinHeight);
    final heroHeaderHeight = heroBackgroundHeight - AppSpacing.pageEdge;
    _heroHeaderHeight = heroHeaderHeight;

    final hasCta = widget.fixedBottomCta != null;

    return Scaffold(
      backgroundColor: widget.backgroundColor,
      body: Stack(
        children: [
          DashboardScrollTemplate(
            scrollController: _scrollController,
            headerHeight: heroHeaderHeight,
            headerBackgroundHeight: heroBackgroundHeight,
            headerBackground: _buildHeroBackground(),
            header: _buildHeroHeader(heroHeaderHeight, navBarHeight),
            sheetOverlapTopPadding: widget.contentOverlapHeight,
            moduleHorizontalMargin: 0,
            content: _buildContent(hasCta),
            bottomReserved: hasCta ? 100 : null,
            onRefresh: widget.onRefresh ?? () async {},
            backgroundColor: widget.backgroundColor,
          ),
          Positioned(
            top: 0,
            left: 0,
            right: 0,
            height: navBarHeight,
            child: _buildNavBarWithBlur(hasTitle),
          ),
          if (hasCta)
            Positioned(
              left: 0,
              right: 0,
              bottom: 0,
              child: _buildFixedBottomCta(context),
            ),
        ],
      ),
    );
  }

  // ─────────────── Hero Background ───────────────

  Widget _buildHeroBackground() {
    if (widget.heroBackground != null) {
      return SizedBox.expand(child: widget.heroBackground);
    }

    final overlay = widget.heroOverlay;
    final imageUrl = widget.heroImageUrl?.trim() ?? '';

    List<Widget> overlayLayers() => [
          if (overlay.tintOpacity > 0)
            Container(color: overlay.tintColor.withValues(alpha: overlay.tintOpacity)),
          if (overlay.gradientStartOpacity > 0 || overlay.gradientEndOpacity > 0)
            DecoratedBox(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: overlay.gradientBegin,
                  end: overlay.gradientEnd,
                  colors: [
                    overlay.tintColor.withValues(alpha: overlay.gradientStartOpacity),
                    overlay.tintColor.withValues(alpha: overlay.gradientEndOpacity),
                  ],
                ),
              ),
            ),
        ];

    if (imageUrl.isNotEmpty) {
      return Stack(
        fit: StackFit.expand,
        children: [
          CachedNetworkImage(
            imageUrl: imageUrl,
            fit: BoxFit.cover,
            width: double.infinity,
            height: double.infinity,
            fadeInDuration: const Duration(milliseconds: 200),
            placeholder: (_, __) => ColoredBox(color: widget.heroFallbackColor),
            errorWidget: (_, __, ___) => ColoredBox(color: widget.heroFallbackColor),
          ),
          ...overlayLayers(),
        ],
      );
    }

    return Stack(
      fit: StackFit.expand,
      children: [
        const DecoratedBox(
          decoration: DashboardHeaderGradient.decoration,
          child: SizedBox.expand(),
        ),
        ...overlayLayers(),
      ],
    );
  }

  // ─────────────── Hero Header ───────────────

  Widget _buildHeroHeader(double heroHeight, double navBarHeight) {
    final hasTitle = widget.title.trim().isNotEmpty;
    final hasSubtitle = (widget.subtitle ?? '').trim().isNotEmpty;
    final hasLabels = widget.labels != null && widget.labels!.isNotEmpty;
    final hasActions = widget.heroActions != null;
    final hasFullBleed = widget.heroFullBleed != null;

    final hasActionsBelow = widget.heroActionsBelowFullBleed != null;
    final showChartArea = hasFullBleed && widget.showChart;
    if (!hasTitle && !hasLabels && !hasActions && !showChartArea && !hasActionsBelow) {
      return const SizedBox.expand();
    }

    final bottomPadding = AppSpacing.s10 + widget.contentOverlapHeight;
    final alignActionsEnd = widget.heroActionsAlignEnd &&
        hasActions &&
        !showChartArea;

    final titleBlock = Padding(
      padding: EdgeInsets.only(
        left: AppSpacing.pageEdge,
        right: AppSpacing.pageEdge,
        bottom: (!alignActionsEnd && hasActions)
            ? LayoutPageLevel2._gapAmountToSubtitle
            : 0,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          if (hasLabels) ...[
            _buildLabels(),
            const SizedBox(height: AppSpacing.md),
          ],
          if (hasTitle)
            Text(
              widget.title,
              style: widget.titleStyle ??
                  AppTypography.headerAppbar.copyWith(
                    color: Colors.white,
                  ),
              textAlign: TextAlign.center,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          if (hasSubtitle) ...[
            const SizedBox(height: AppSpacing.sm),
            Text(
              widget.subtitle!,
              style: widget.subtitleStyle ??
                  AppTypography.amountPrimary.copyWith(
                    color: Colors.white,
                  ),
              textAlign: TextAlign.center,
              maxLines: 3,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ],
      ),
    );

    final heroActionsBlock = hasActions
        ? Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.pageEdge),
            child: Center(child: widget.heroActions!),
          )
        : null;

    if (alignActionsEnd) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SizedBox(height: navBarHeight + AppSpacing.pageEdge),
          if (hasTitle || hasLabels || hasSubtitle) titleBlock,
          const Expanded(child: SizedBox.shrink()),
          if (heroActionsBlock != null) heroActionsBlock,
          if (hasActionsBelow)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: AppSpacing.pageEdge),
              child: widget.heroActionsBelowFullBleed!,
            ),
          // Marge bas du hero gérée dans [heroActions] (ex. 36 px sous le CTA).
          SizedBox(height: widget.heroActionsAlignEnd ? 0 : bottomPadding),
        ],
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // ── Nav bar + gap ──
        SizedBox(height: navBarHeight + AppSpacing.pageEdge),

        // ── Balance module (titre + montant + sous-titre) ──
        if (hasTitle || hasLabels || hasSubtitle) titleBlock,

        // ── heroActions (ex. "1 placement", IBAN) ──
        if (heroActionsBlock != null) heroActionsBlock,

        // ── remainingSpaceBalanceModule ──
        if (showChartArea)
          Expanded(
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: AppSpacing.sm),
              child: widget.heroFullBleed!,
            ),
          )
        else
          const Spacer(),

        if (hasActionsBelow)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.pageEdge),
            child: widget.heroActionsBelowFullBleed!,
          ),

        SizedBox(height: bottomPadding),
      ],
    );
  }

  Widget _buildLabels() {
    return Wrap(
      spacing: AppSpacing.sm,
      runSpacing: AppSpacing.xs,
      alignment: WrapAlignment.center,
      children: widget.labels!.map((label) {
        return GlassBadge(
          text: label.text,
          opacity: GlassBadgeOpacity.light,
        );
      }).toList(),
    );
  }

  // ─────────────── Nav Bar ───────────────

  static const double _navBlurSigma = 20;

  Widget _buildNavBarWithBlur(bool hasTitle) {
    final t = _navTitleOpacity;
    final sigma = _navBlurSigma * t;

    final fgColor = Color.lerp(
      widget.navBarForegroundColor,
      AppColors.textPrimary,
      t,
    )!;

    final navBar = AppTopNavBar(
      leadingType: widget.leadingType,
      onBackTap: widget.onLeadingTap ?? () => Navigator.of(context).pop(),
      onCloseTap: widget.onLeadingTap ?? () => Navigator.of(context).pop(),
      onProfileTap: widget.onLeadingTap,
      profileInitials: widget.profileInitials,
      actions: widget.navBarActions,
      backgroundColor: Colors.transparent,
      foregroundColor: fgColor,
      useDashboardStyle: false,
      title: hasTitle ? widget.title : null,
      titleOpacity: t,
      centerTitle: true,
      titleTextStyle: AppTypography.itemPrimary.copyWith(
        color: fgColor,
      ),
    );

    if (t <= 0.01) return navBar;

    return ClipRect(
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: sigma, sigmaY: sigma),
        child: Container(
          color: widget.backgroundColor.withValues(alpha: 0.6 * t),
          child: navBar,
        ),
      ),
    );
  }

  // ─────────────── Content ───────────────

  Widget _buildContent(bool hasCta) {
    final gap = widget.moduleSpacing;
    final padding = widget.contentPadding;
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (final w in widget.content) ...[
          padding != null ? Padding(padding: padding, child: w) : w,
          SizedBox(height: gap),
        ],
        if (widget.footerContent != null) ...[
          widget.footerContent!,
          const SizedBox(height: AppSpacing.lg),
        ],
        SizedBox(height: hasCta ? 80 : AppSpacing.xxl),
      ],
    );
  }

  // ─────────────── Fixed Bottom CTA ───────────────

  Widget _buildFixedBottomCta(BuildContext context) {
    final cta = widget.fixedBottomCta!;
    final bottomInset = MediaQuery.paddingOf(context).bottom;
    return ClipRect(
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 16, sigmaY: 16),
        child: Container(
          width: double.infinity,
          padding: EdgeInsets.fromLTRB(
            AppSpacing.pageEdge,
            2,
            AppSpacing.pageEdge,
            AppSpacing.md + bottomInset,
          ),
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: [
                widget.backgroundColor.withValues(alpha: 0.0),
                widget.backgroundColor.withValues(alpha: 0.72),
                widget.backgroundColor.withValues(alpha: 0.94),
              ],
            ),
          ),
          child: SizedBox(
            width: double.infinity,
            height: 56,
            child: FilledButton(
              onPressed: cta.onTap,
              style: FilledButton.styleFrom(
                backgroundColor: AppColors.textPrimary,
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(999),
                ),
                textStyle: AppTypography.titleMedium.copyWith(
                  fontWeight: FontWeight.w600,
                  height: 1,
                ),
              ),
              child: Text(cta.label),
            ),
          ),
        ),
      ),
    );
  }
}
