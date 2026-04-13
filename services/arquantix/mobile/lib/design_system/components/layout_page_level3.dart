import 'dart:ui';

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../../features/wallet/widgets/dashboard_scroll_template.dart';
import '../atoms/app_colors.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';
import 'app_top_nav_bar.dart';
import 'glass_badge.dart';
import 'layout_page_level2.dart';

// ─────────────────────────────────────────────────────────────────────────────
// LayoutPageLevel3 — Compact detail page scaffold (no chart).
//
// Identical to LayoutPageLevel2 except:
//   • Hero height is NOT a screen percentage — it wraps its content.
//   • No heroFullBleed / showChart support.
//   • Hero height = navBar + balance module + heroActions
//                   + 2 × margin + heroActionsBelowFullBleed + bottom padding.
// ─────────────────────────────────────────────────────────────────────────────

class LayoutPageLevel3 extends StatefulWidget {
  static const double gapAmountToSubtitle = 8;
  static const double marginBelowBalance = AppSpacing.pageEdge;

  const LayoutPageLevel3({
    super.key,
    // ── Hero ──
    this.heroImageUrl,
    this.heroBackground,
    this.heroFallbackColor = const Color(0xFF0D1B2A),
    this.heroOverlay = HeroOverlayConfig.standard,
    // ── Title area ──
    this.title = '',
    this.titleStyle,
    this.subtitle,
    this.subtitleStyle,
    this.labels,
    this.heroActions,
    this.heroActionsBelowFullBleed,
    // ── Nav bar ──
    this.leadingType = AppTopNavBarLeading.back,
    this.onLeadingTap,
    this.navBarActions = const [],
    this.navBarForegroundColor = Colors.white,
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
  final String? heroImageUrl;
  final Widget? heroBackground;
  final Color heroFallbackColor;
  final HeroOverlayConfig heroOverlay;

  // ── Title area ──
  final String title;
  final TextStyle? titleStyle;
  final String? subtitle;
  final TextStyle? subtitleStyle;
  final List<LayoutPageLabel>? labels;
  final Widget? heroActions;
  final Widget? heroActionsBelowFullBleed;

  // ── Nav bar ──
  final AppTopNavBarLeading leadingType;
  final VoidCallback? onLeadingTap;
  final List<AppTopNavBarAction> navBarActions;
  final Color navBarForegroundColor;

  // ── Content ──
  final List<Widget> content;
  final double contentOverlapHeight;
  final double moduleSpacing;
  final EdgeInsetsGeometry? contentPadding;
  final Widget? footerContent;

  // ── Bottom CTA ──
  final ({String label, VoidCallback onTap})? fixedBottomCta;

  // ── Behavior ──
  /// Si null, rafraîchissement vide (pull-to-refresh toujours disponible).
  final Future<void> Function()? onRefresh;
  final Color backgroundColor;

  @override
  State<LayoutPageLevel3> createState() => _LayoutPageLevel3State();
}

class _LayoutPageLevel3State extends State<LayoutPageLevel3> {
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
    final topPadding = MediaQuery.paddingOf(context).top;
    final navBarHeight = topPadding + kToolbarHeight;

    final hasTitle = widget.title.trim().isNotEmpty;
    final hasSubtitle = (widget.subtitle ?? '').trim().isNotEmpty;
    final hasLabels = widget.labels != null && widget.labels!.isNotEmpty;
    final hasActions = widget.heroActions != null;
    final hasActionsBelow = widget.heroActionsBelowFullBleed != null;

    // Fixed hero height: sum of all header modules.
    double heroHeight = navBarHeight + AppSpacing.pageEdge;
    if (hasLabels) heroHeight += 30 + AppSpacing.md;
    if (hasTitle) heroHeight += 42;
    if (hasSubtitle) heroHeight += AppSpacing.sm + 22;
    if (hasActions) heroHeight += LayoutPageLevel3.gapAmountToSubtitle + 30;
    heroHeight += LayoutPageLevel3.marginBelowBalance;
    if (hasActionsBelow) heroHeight += 78;
    heroHeight += AppSpacing.s10 + widget.contentOverlapHeight;

    _heroHeaderHeight = heroHeight;
    final heroBackgroundHeight = heroHeight + AppSpacing.pageEdge;

    final hasCta = widget.fixedBottomCta != null;

    return Scaffold(
      backgroundColor: widget.backgroundColor,
      body: Stack(
        children: [
          DashboardScrollTemplate(
            scrollController: _scrollController,
            headerHeight: heroHeight,
            headerBackgroundHeight: heroBackgroundHeight,
            headerBackground: _buildHeroBackground(),
            header: _buildHeroHeader(heroHeight, navBarHeight),
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

    final imageUrl = (widget.heroImageUrl ?? '').trim();
    final overlay = widget.heroOverlay;

    return Stack(
      fit: StackFit.expand,
      children: [
        if (imageUrl.isNotEmpty)
          CachedNetworkImage(
            imageUrl: imageUrl,
            fit: BoxFit.cover,
            placeholder: (_, __) => Container(color: widget.heroFallbackColor),
            errorWidget: (_, __, ___) => Container(color: widget.heroFallbackColor),
          )
        else
          Container(color: widget.heroFallbackColor),
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
      ],
    );
  }

  // ─────────────── Hero Header ───────────────

  Widget _buildHeroHeader(double heroHeight, double navBarHeight) {
    final hasTitle = widget.title.trim().isNotEmpty;
    final hasSubtitle = (widget.subtitle ?? '').trim().isNotEmpty;
    final hasLabels = widget.labels != null && widget.labels!.isNotEmpty;
    final hasActions = widget.heroActions != null;
    final hasActionsBelow = widget.heroActionsBelowFullBleed != null;

    if (!hasTitle && !hasLabels && !hasActions && !hasActionsBelow) {
      return const SizedBox.expand();
    }

    return SizedBox(
      height: heroHeight,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SizedBox(height: navBarHeight + AppSpacing.pageEdge),

          Padding(
            padding: EdgeInsets.only(
              left: AppSpacing.pageEdge,
              right: AppSpacing.pageEdge,
              bottom: hasActions ? LayoutPageLevel3.gapAmountToSubtitle : 0,
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
          ),

          if (hasActions)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: AppSpacing.pageEdge),
              child: Center(child: widget.heroActions!),
            ),

          SizedBox(height: LayoutPageLevel3.marginBelowBalance),

          if (hasActionsBelow)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: AppSpacing.pageEdge),
              child: widget.heroActionsBelowFullBleed!,
            ),

          SizedBox(height: AppSpacing.s10 + widget.contentOverlapHeight),
        ],
      ),
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
