import 'dart:ui';

import 'package:flutter/material.dart';

import '../../features/wallet/widgets/dashboard_scroll_template.dart';
import '../atoms/app_colors.dart';
import '../atoms/dashboard_header_gradient.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';
import 'app_top_nav_bar.dart';
import 'glass_badge.dart';

/// Label chip displayed above the title in the hero area.
class LayerPageLabel {
  const LayerPageLabel({
    required this.text,
    this.backgroundColor,
    this.textColor,
  });

  final String text;
  final Color? backgroundColor;
  final Color? textColor;
}

/// Reusable Level 2 detail page with hero background (dégradé) + transparent nav bar.
///
/// Layout (top to bottom):
/// 1. Background gradient covering ~70% of the screen
/// 2. Transparent [AppTopNavBar] overlay (glass-blur disk buttons)
/// 3. Centered labels (optional chips), title, subtitle over the image
/// 4. Hero action buttons below subtitle (optional, e.g. ActionButtonRow)
/// 5. First content module overlapping the bottom of the hero image
/// 6. Scrollable module content below
///
/// Scroll-driven: title fades into the nav bar as user scrolls.
class LayerPageLevel2 extends StatefulWidget {
  const LayerPageLevel2({
    super.key,
    this.heroImageUrl,
    this.heroBackground,
    this.heroHeightFraction = 0.60,
    required this.title,
    this.titleSubtitle,
    this.labels,
    this.heroActionButtons,
    this.leadingType = AppTopNavBarLeading.back,
    this.onLeadingTap,
    this.navBarActions = const [],
    required this.content,
    this.footerContent,
    this.fixedBottomCta,
    this.onRefresh,
    this.heroGradientColors,
    this.contentOverlapHeight = 0,
  });

  /// URL of the hero background image.
  final String? heroImageUrl;

  /// Custom hero background widget (takes priority over [heroImageUrl]).
  final Widget? heroBackground;

  /// Fraction of screen height for the hero area (0.0–1.0).
  final double heroHeightFraction;

  /// Page title (centered, white, bold) shown in the hero area.
  final String title;

  /// Subtitle below the title (centered, white, lighter).
  final String? titleSubtitle;

  /// Label chips displayed above the title (e.g. risk label, rate).
  final List<LayerPageLabel>? labels;

  /// Widget displayed below the subtitle in the hero area.
  /// Typically an [ActionButtonRow] with hero-style buttons.
  final Widget? heroActionButtons;

  /// Leading button type in the nav bar.
  final AppTopNavBarLeading leadingType;

  /// Called when the leading button is tapped. Defaults to Navigator.pop.
  final VoidCallback? onLeadingTap;

  /// Action buttons on the right side of the nav bar.
  final List<AppTopNavBarAction> navBarActions;

  /// Scrollable content widgets (modules). The first one will overlap the hero.
  final List<Widget> content;

  /// Optional footer widget at the very bottom of the scroll.
  final Widget? footerContent;

  /// Fixed bottom call-to-action button.
  final ({String label, VoidCallback onTap})? fixedBottomCta;

  /// Pull-to-refresh callback.
  final Future<void> Function()? onRefresh;

  /// Custom gradient colors over the hero image.
  final List<Color>? heroGradientColors;

  /// How many pixels the first content module overlaps the hero image.
  final double contentOverlapHeight;

  @override
  State<LayerPageLevel2> createState() => _LayerPageLevel2State();
}

class _LayerPageLevel2State extends State<LayerPageLevel2> {
  final ScrollController _scrollController = ScrollController();
  double _navTitleOpacity = 0;

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
    final next = ((offset - 30) / 50).clamp(0.0, 1.0);
    if ((next - _navTitleOpacity).abs() > 0.02) {
      setState(() => _navTitleOpacity = next);
    }
  }

  @override
  Widget build(BuildContext context) {
    final screenHeight = MediaQuery.sizeOf(context).height;
    final topPadding = MediaQuery.paddingOf(context).top;
    final heroBackgroundHeight = screenHeight * widget.heroHeightFraction;
    final heroHeaderHeight = heroBackgroundHeight - AppSpacing.pageEdge * 1.5;
    final navBarHeight = topPadding + kToolbarHeight;
    final hasTitle = widget.title.trim().isNotEmpty;
    final hasCta = widget.fixedBottomCta != null;

    return Scaffold(
      backgroundColor: AppColors.pageBackground,
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
            backgroundColor: AppColors.pageBackground,
          ),
          Positioned(
            top: 0,
            left: 0,
            right: 0,
            height: navBarHeight,
            child: _buildNavBar(hasTitle),
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

  // ── Hero background ──

  Widget _buildHeroBackground() {
    if (widget.heroBackground != null) {
      return SizedBox.expand(child: widget.heroBackground);
    }

    return const DecoratedBox(
      decoration: DashboardHeaderGradient.decoration,
      child: SizedBox.expand(),
    );
  }

  // ── Hero header (labels → title → subtitle → action buttons) ──

  Widget _buildHeroHeader(double heroHeight, double navBarHeight) {
    final hasTitle = widget.title.trim().isNotEmpty;
    final hasSubtitle = (widget.titleSubtitle ?? '').trim().isNotEmpty;
    final hasLabels = widget.labels != null && widget.labels!.isNotEmpty;
    final hasActions = widget.heroActionButtons != null;

    if (!hasTitle && !hasLabels && !hasActions) return const SizedBox.expand();

    return Padding(
      padding: EdgeInsets.only(
        left: AppSpacing.pageEdge,
        right: AppSpacing.pageEdge,
        top: navBarHeight + AppSpacing.md,
        bottom: AppSpacing.xl + widget.contentOverlapHeight,
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.end,
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          if (hasLabels) ...[
            _buildLabels(),
            const SizedBox(height: AppSpacing.md),
          ],
          if (hasTitle)
            Text(
              widget.title,
              style: AppTypography.headerAppbar.copyWith(
                color: Colors.white,
              ),
              textAlign: TextAlign.center,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
          if (hasSubtitle) ...[
            const SizedBox(height: AppSpacing.xs),
            Text(
              widget.titleSubtitle!,
              style: AppTypography.amountPrimary.copyWith(
                color: Colors.white,
              ),
              textAlign: TextAlign.center,
              maxLines: 3,
              overflow: TextOverflow.ellipsis,
            ),
          ],
          if (hasActions) ...[
            const SizedBox(height: AppSpacing.lg),
            widget.heroActionButtons!,
          ],
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

  // ── Transparent nav bar ──

  Widget _buildNavBar(bool hasTitle) {
    return AppTopNavBar(
      leadingType: widget.leadingType,
      onBackTap: widget.onLeadingTap ?? () => Navigator.of(context).pop(),
      onCloseTap: widget.onLeadingTap ?? () => Navigator.of(context).pop(),
      onProfileTap: widget.onLeadingTap,
      actions: widget.navBarActions,
      backgroundColor: Colors.transparent,
      foregroundColor: Colors.white,
      useDashboardStyle: true,
      title: hasTitle ? widget.title : null,
      titleOpacity: _navTitleOpacity,
      centerTitle: true,
      titleTextStyle: AppTypography.itemPrimary.copyWith(
        color: Colors.white,
      ),
    );
  }

  // ── Scrollable content ──

  Widget _buildContent(bool hasCta) {
    final moduleGap = DashboardLayoutConstants.moduleGap;
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        ...widget.content.expand((w) => [w, SizedBox(height: moduleGap)]),
        if (widget.footerContent != null) ...[
          widget.footerContent!,
          const SizedBox(height: AppSpacing.lg),
        ],
        SizedBox(height: hasCta ? 80 : AppSpacing.xxl),
      ],
    );
  }

  // ── Fixed bottom CTA ──

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
                AppColors.pageBackground.withValues(alpha: 0.0),
                AppColors.pageBackground.withValues(alpha: 0.72),
                AppColors.pageBackground.withValues(alpha: 0.94),
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
