import 'dart:math' as math;
import 'dart:ui';

import 'package:flutter/material.dart';

import '../../features/markets/presentation/widgets/chart_asset_module.dart';
import '../../features/wallet/widgets/dashboard_scroll_template.dart';
import '../atoms/app_colors.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';
import 'app_top_nav_bar.dart';
import 'article_hero_header.dart' show ArticleCategoryBadgeData;
import 'category_badge.dart';

// ─────────────────────────────────────────────────────────────────────────────
// LayoutPageInstrumentDetail — Détail instrument / bundle crypto sur fond gris.
//
// Puces au-dessus du titre : [CategoryBadge] + [ArticleCategoryBadgeData], identiques
// à [ArticleHeroHeader] (offre exclusive, article) — fond blanc, point coloré, pas de variante dark/light.
// ─────────────────────────────────────────────────────────────────────────────

/// Gabarit détail instrument : fond gris uni, navbar claire, titre aligné à gauche.
class LayoutPageInstrumentDetail extends StatefulWidget {
  /// Figma : 8px entre puces, nom d’instrument, prix et ligne de performance.
  static const double _headerStackGapPx = AppSpacing.s2;

  /// Figma : espace entre l’avatar instrument (24×24) et le libellé.
  static const double _titleLeadingGapPx = 6;

  /// Figma : espace entre la **ligne perf** (puces) et la **rangée Acheter / Vendre** — 16 + 4 px.
  static const double _gapPerformanceRowToActionButtonsPx =
      AppSpacing.lg + AppSpacing.s1;

  /// Hauteur d’une rangée de boutons [AppPrimaryButtonSize.medium] (Acheter / Vendre).
  static const double _heroActionsRowHeightPx = 48;

  /// Hauteur « corps » typique du slot [heroActions] hors marge avec le sous-titre :
  /// ligne type [InstrumentDetailHeroSupportingLine] (lh 18) + [AppSpacing.md] + rangée CTA 48 px
  /// (ex. détail transaction : date + boutons Justifier / Télécharger).
  static const double _heroActionsBlockBodyEstimatePx =
      18 + AppSpacing.md + _heroActionsRowHeightPx;

  /// Estime la hauteur des blocs entre le [SizedBox] top (nav + pageEdge) et le padding bas du hero.
  static double _estimateHeroBodyContentHeight({
    required bool hasCategoryBadges,
    required bool hasTitle,
    required bool hasTitleDescription,
    required bool hasSubtitle,
    required bool showChartArea,
    required bool hasActions,
    required bool hasActionsBelow,
    required bool alignActionsEnd,
    required double chartAreaHeightPx,
  }) {
    double contentEstimate = 0;
    if (hasCategoryBadges) {
      contentEstimate += 30 + LayoutPageInstrumentDetail._headerStackGapPx;
    }
    if (hasTitle) contentEstimate += 38;
    if (hasTitleDescription) {
      contentEstimate +=
          LayoutPageInstrumentDetail._headerStackGapPx + 52;
    }
    if (hasSubtitle) {
      contentEstimate +=
          LayoutPageInstrumentDetail._headerStackGapPx + 26;
    }
    if (showChartArea) {
      contentEstimate += chartAreaHeightPx;
    }
    if (hasActions) {
      contentEstimate += LayoutPageInstrumentDetail._headerStackGapPx +
          (alignActionsEnd
              ? 320
              : LayoutPageInstrumentDetail._heroActionsBlockBodyEstimatePx);
    }
    if (hasActionsBelow) {
      contentEstimate +=
          LayoutPageInstrumentDetail._gapPerformanceRowToActionButtonsPx +
          LayoutPageInstrumentDetail._heroActionsRowHeightPx;
    }
    if (hasActionsBelow && showChartArea) {
      contentEstimate += AppSpacing.sm;
    }
    return contentEstimate;
  }

  const LayoutPageInstrumentDetail({
    super.key,
    this.title = '',
    this.titleLeading,
    this.titleStyle,
    this.subtitle,
    this.subtitleStyle,
    /// Texte d’accroche sous le [title] (ex. sous-titre CMS TitlePage bundle), au-dessus du [subtitle] (montant NAV).
    this.titleDescription,
    this.categoryBadges,
    this.heroActions,
    this.heroFullBleed,
    this.heroActionsBelowFullBleed,
    this.showChart = true,
    this.heroActionsAlignEnd = false,
    this.leadingType = AppTopNavBarLeading.back,
    this.onLeadingTap,
    this.navBarActions = const [],
    this.navBarForegroundColor = AppColors.textPrimary,
    this.profileInitials = 'JA',
    required this.content,
    this.contentOverlapHeight = 0,
    this.moduleSpacing = AppSpacing.xl,
    /// Espace sous le hero (avant le 1er module scrollé), en plus des [moduleSpacing] entre modules.
    /// Défaut **40 px** ([AppSpacing.s10]) — premier module ou bloc scrollé, quel que soit le type.
    this.contentTopSpacing = AppSpacing.s10,
    this.contentPadding,
    this.footerContent,
    this.fixedBottomCta,
    this.onRefresh,
    this.backgroundColor = AppColors.pageBackground,
    this.heroHeightFraction = 0.72,
    this.heroMinHeight,
    /// Si true (défaut) : hauteur du hero = somme des blocs (titre, graph, etc.), sans remplir un % d’écran
    /// ni [Expanded] sous le chart — évite le vide gris entre le disclaimer et le scroll.
    /// Si false : ancien comportement `max(72 % écran, min)` + zone chart étirable.
    this.tightHeroHeight = true,
    /// Trait noir pleine largeur sous le hero + pastille debug ([DashboardScrollTemplate.debugHeaderBottomEdge]).
    this.debugShowHeaderBottomEdge = false,
    /// Hauteur estimée du bloc chart en hero (défaut : instrument). Ex. bundle performance.
    this.heroChartAreaEstimatedHeight,
  });

  final String title;
  /// À gauche du [title] (avatar instrument 24×24 DS), espacement [_titleLeadingGapPx].
  final Widget? titleLeading;
  /// Défaut : [AppTypography.headerTertiary] (page/headerTertiary) + [AppColors.textPrimary].
  final TextStyle? titleStyle;
  final String? subtitle;
  /// Défaut : [AppTypography.amountPrimary] + [AppColors.textPrimary] (montant principal).
  final TextStyle? subtitleStyle;
  /// Sous le titre, au-dessus du montant [subtitle] — ex. champ `subtitle` du module TitlePage (CMS).
  final String? titleDescription;
  /// Même rendu que les badges du hero offre exclusive / article ([CategoryBadge]).
  final List<ArticleCategoryBadgeData>? categoryBadges;
  final Widget? heroActions;
  final Widget? heroFullBleed;
  final Widget? heroActionsBelowFullBleed;
  final bool showChart;
  final bool heroActionsAlignEnd;

  final AppTopNavBarLeading leadingType;
  final VoidCallback? onLeadingTap;
  final List<AppTopNavBarAction> navBarActions;
  final Color navBarForegroundColor;
  final String profileInitials;

  final List<Widget> content;
  final double contentOverlapHeight;
  final double moduleSpacing;
  /// Marge verticale entre la fin du hero et le premier bloc du body scrollé.
  final double contentTopSpacing;
  final EdgeInsetsGeometry? contentPadding;
  final Widget? footerContent;
  final ({String label, VoidCallback onTap})? fixedBottomCta;
  final Future<void> Function()? onRefresh;
  final Color backgroundColor;

  /// Fraction de la hauteur d’écran pour la zone hero (titre + graphique intégré).
  final double heroHeightFraction;
  final double? heroMinHeight;

  /// Hero calé sur le contenu (pas de grand bloc vide sous le chart).
  final bool tightHeroHeight;

  /// Active le repère visuel bas de header (debug espacement hero / contenu scroll).
  final bool debugShowHeaderBottomEdge;

  /// Si non null, remplace [ChartAssetModule.instrumentDetailEstimatedHeightPx] pour l’estimation du hero.
  final double? heroChartAreaEstimatedHeight;

  @override
  State<LayoutPageInstrumentDetail> createState() =>
      _LayoutPageInstrumentDetailState();
}

class _LayoutPageInstrumentDetailState extends State<LayoutPageInstrumentDetail> {
  final ScrollController _scrollController = ScrollController();
  /// Mesure la hauteur réelle du [Column] « tight » (évite un grand vide sous le chart).
  final GlobalKey _tightHeroColumnKey = GlobalKey();
  double? _measuredTightHeroHeight;
  /// Dernière estimation « corps » du hero ; si elle change (ex. ligne perf qui apparaît), on invalide la mesure.
  double? _lastHeroBodyEstimate;
  double _navTitleOpacity = 0;
  double _heroHeaderHeight = 0;

  void _reportTightHeroHeightAfterLayout() {
    if (!mounted) return;
    final ctx = _tightHeroColumnKey.currentContext;
    if (ctx == null) return;
    final box = ctx.findRenderObject() as RenderBox?;
    if (box == null || !box.hasSize) return;
    final h = box.size.height;
    if (_measuredTightHeroHeight != null &&
        (h - _measuredTightHeroHeight!).abs() < 0.5) {
      return;
    }
    setState(() => _measuredTightHeroHeight = h);
  }

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
    // Blur dès un court scroll : le titre passe tôt sous la barre sur ce layout.
    final start = _heroHeaderHeight * 0.10;
    final range = _heroHeaderHeight * 0.16;
    final next = range > 0
        ? ((offset - start) / range).clamp(0.0, 1.0)
        : 0.0;
    if ((next - _navTitleOpacity).abs() > 0.02) {
      setState(() => _navTitleOpacity = next);
    }
  }

  @override
  Widget build(BuildContext context) {
    final screenHeight = MediaQuery.sizeOf(context).height;
    final topPadding = MediaQuery.paddingOf(context).top;
    final navBarHeight = topPadding + kToolbarHeight;

    final hasTitle = widget.title.trim().isNotEmpty;
    final hasTitleDescription = hasTitle &&
        (widget.titleDescription ?? '').trim().isNotEmpty;
    final hasSubtitle = (widget.subtitle ?? '').trim().isNotEmpty;
    final hasCategoryBadges =
        widget.categoryBadges != null && widget.categoryBadges!.isNotEmpty;
    final hasActions = widget.heroActions != null;
    final hasFullBleed = widget.heroFullBleed != null;
    final hasActionsBelow = widget.heroActionsBelowFullBleed != null;
    final showChartArea = hasFullBleed && widget.showChart;
    final alignActionsEnd = widget.heroActionsAlignEnd &&
        widget.heroActions != null &&
        !showChartArea;

    final chartAreaHeightPx = widget.heroChartAreaEstimatedHeight ??
        ChartAssetModule.instrumentDetailEstimatedHeightPx;
    final bodyEstimate = LayoutPageInstrumentDetail._estimateHeroBodyContentHeight(
      hasCategoryBadges: hasCategoryBadges,
      hasTitle: hasTitle,
      hasTitleDescription: hasTitleDescription,
      hasSubtitle: hasSubtitle,
      showChartArea: showChartArea,
      hasActions: hasActions,
      hasActionsBelow: hasActionsBelow,
      alignActionsEnd: alignActionsEnd,
      chartAreaHeightPx: chartAreaHeightPx,
    );

    late final double heroBackgroundHeight;
    late final double heroHeaderHeight;

    // Sans graphique + actions en bas de bloc, le hero garde un [Expanded] : ne pas utiliser la hauteur « tight ».
    final useTightHero =
        widget.tightHeroHeight && !alignActionsEnd;

    if (useTightHero) {
      if (_lastHeroBodyEstimate != null &&
          (bodyEstimate - _lastHeroBodyEstimate!).abs() > 0.5) {
        _measuredTightHeroHeight = null;
      }
      _lastHeroBodyEstimate = bodyEstimate;

      // Pas de marge sous le disclaimer (compliance) : la phrase touche le bas du header (sauf [contentOverlapHeight]).
      var fallback = navBarHeight +
          AppSpacing.pageEdge +
          bodyEstimate +
          widget.contentOverlapHeight;
      if (widget.heroMinHeight != null) {
        fallback = math.max(fallback, widget.heroMinHeight!);
      }
      heroHeaderHeight = _measuredTightHeroHeight ?? fallback;
      heroBackgroundHeight = heroHeaderHeight + AppSpacing.pageEdge;
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _reportTightHeroHeightAfterLayout();
      });
    } else {
      _lastHeroBodyEstimate = null;
      final safeMinHeight = navBarHeight +
          AppSpacing.md +
          bodyEstimate +
          AppSpacing.xl +
          widget.contentOverlapHeight +
          AppSpacing.pageEdge;

      final fractionHeight = screenHeight * widget.heroHeightFraction;
      heroBackgroundHeight =
          math.max(fractionHeight, widget.heroMinHeight ?? safeMinHeight);
      heroHeaderHeight = heroBackgroundHeight - AppSpacing.pageEdge;
    }
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
            scrollContentTopSpacing: widget.contentTopSpacing,
            moduleHorizontalMargin: 0,
            content: _buildContent(hasCta),
            bottomReserved: hasCta ? 100 : null,
            onRefresh: widget.onRefresh ?? () async {},
            backgroundColor: widget.backgroundColor,
            debugHeaderBottomEdge: widget.debugShowHeaderBottomEdge,
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

  Widget _buildHeroBackground() {
    return ColoredBox(color: widget.backgroundColor);
  }

  Widget _buildHeroHeader(double heroHeight, double navBarHeight) {
    final hasTitle = widget.title.trim().isNotEmpty;
    final hasTitleDescription = hasTitle &&
        (widget.titleDescription ?? '').trim().isNotEmpty;
    final hasSubtitle = (widget.subtitle ?? '').trim().isNotEmpty;
    final hasCategoryBadges =
        widget.categoryBadges != null && widget.categoryBadges!.isNotEmpty;
    final hasActions = widget.heroActions != null;
    final hasFullBleed = widget.heroFullBleed != null;
    final hasActionsBelow = widget.heroActionsBelowFullBleed != null;
    final showChartArea = hasFullBleed && widget.showChart;

    if (!hasTitle &&
        !hasCategoryBadges &&
        !hasActions &&
        !showChartArea &&
        !hasActionsBelow) {
      return const SizedBox.expand();
    }

    final alignActionsEnd = widget.heroActionsAlignEnd &&
        hasActions &&
        !showChartArea;
    final useTightColumn = widget.tightHeroHeight && !alignActionsEnd;
    /// Sous le chart : 0 px en mode tight (phrase compliance au bas du header), sinon marge classique + overlap scroll.
    final bottomPadding = useTightColumn
        ? widget.contentOverlapHeight
        : AppSpacing.s10 + widget.contentOverlapHeight;

    final titleBlock = Padding(
      padding: EdgeInsets.only(
        left: AppSpacing.pageEdge,
        right: AppSpacing.pageEdge,
        bottom: (!alignActionsEnd && hasActions)
            ? LayoutPageInstrumentDetail._headerStackGapPx
            : 0,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (hasCategoryBadges) ...[
            _buildCategoryBadges(),
            const SizedBox(height: LayoutPageInstrumentDetail._headerStackGapPx),
          ],
          if (hasTitle)
            widget.titleLeading != null
                ? Row(
                    crossAxisAlignment: CrossAxisAlignment.center,
                    children: [
                      widget.titleLeading!,
                      const SizedBox(
                        width: LayoutPageInstrumentDetail._titleLeadingGapPx,
                      ),
                      Expanded(
                        child: Text(
                          widget.title,
                          style: widget.titleStyle ??
                              AppTypography.headerTertiary.copyWith(
                                color: AppColors.textPrimary,
                              ),
                          textAlign: TextAlign.start,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                    ],
                  )
                : Text(
                    widget.title,
                    style: widget.titleStyle ??
                        AppTypography.headerTertiary.copyWith(
                          color: AppColors.textPrimary,
                        ),
                    textAlign: TextAlign.start,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
          if (hasTitleDescription) ...[
            const SizedBox(height: LayoutPageInstrumentDetail._headerStackGapPx),
            Text(
              widget.titleDescription!.trim(),
              style: AppTypography.bodyRegular.copyWith(
                color: AppColors.textPrimary,
              ),
              textAlign: TextAlign.start,
            ),
          ],
          if (hasSubtitle) ...[
            const SizedBox(height: LayoutPageInstrumentDetail._headerStackGapPx),
            Text(
              widget.subtitle!,
              style: (widget.subtitleStyle ??
                      AppTypography.amountPrimary.copyWith(
                        color: AppColors.textPrimary,
                      ))
                  .copyWith(inherit: false),
              textAlign: TextAlign.start,
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
            child: Align(
              alignment: Alignment.centerLeft,
              child: widget.heroActions!,
            ),
          )
        : null;

    if (alignActionsEnd) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SizedBox(height: navBarHeight + AppSpacing.pageEdge),
          if (hasTitle || hasCategoryBadges || hasSubtitle) titleBlock,
          const Expanded(child: SizedBox.shrink()),
          if (heroActionsBlock != null) heroActionsBlock,
          if (heroActionsBlock != null && hasActionsBelow)
            const SizedBox(
              height: LayoutPageInstrumentDetail._gapPerformanceRowToActionButtonsPx,
            ),
          if (hasActionsBelow)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: AppSpacing.pageEdge),
              child: widget.heroActionsBelowFullBleed!,
            ),
          SizedBox(height: widget.heroActionsAlignEnd ? 0 : bottomPadding),
        ],
      );
    }

    if (useTightColumn) {
      return Column(
        key: _tightHeroColumnKey,
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SizedBox(height: navBarHeight + AppSpacing.pageEdge),
          if (hasTitle || hasCategoryBadges || hasSubtitle) titleBlock,
          if (heroActionsBlock != null) heroActionsBlock,
          if (heroActionsBlock != null && hasActionsBelow)
            const SizedBox(
              height: LayoutPageInstrumentDetail._gapPerformanceRowToActionButtonsPx,
            ),
          if (hasActionsBelow)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: AppSpacing.pageEdge),
              child: widget.heroActionsBelowFullBleed!,
            ),
          if (hasActionsBelow && showChartArea) const SizedBox(height: AppSpacing.sm),
          if (showChartArea) widget.heroFullBleed! else const SizedBox.shrink(),
          if (bottomPadding > 0) SizedBox(height: bottomPadding),
        ],
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        SizedBox(height: navBarHeight + AppSpacing.pageEdge),
        if (hasTitle || hasCategoryBadges || hasSubtitle) titleBlock,
        if (heroActionsBlock != null) heroActionsBlock,
        if (heroActionsBlock != null && hasActionsBelow)
          const SizedBox(
            height: LayoutPageInstrumentDetail._gapPerformanceRowToActionButtonsPx,
          ),
        if (hasActionsBelow)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.pageEdge),
            child: widget.heroActionsBelowFullBleed!,
          ),
        if (hasActionsBelow && showChartArea) const SizedBox(height: AppSpacing.sm),
        if (showChartArea)
          Expanded(
            child: widget.heroFullBleed!,
          )
        else
          const Spacer(),
        SizedBox(height: bottomPadding),
      ],
    );
  }

  /// Aligné sur [ArticleHeroHeader._buildTitleArea] (offre exclusive / article).
  Widget _buildCategoryBadges() {
    return Wrap(
      spacing: AppSpacing.s2,
      runSpacing: AppSpacing.s1,
      alignment: WrapAlignment.start,
      children: widget.categoryBadges!
          .map((b) => CategoryBadge(label: b.label, dotColor: b.dotColor))
          .toList(),
    );
  }

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
      titleTextStyle: AppTypography.headerTertiary.copyWith(
        color: fgColor,
      ),
    );

    if (t <= 0.01) return navBar;

    return ClipRect(
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: sigma, sigmaY: sigma),
        child: Container(
          color: widget.backgroundColor.withValues(alpha: 0.72 * t),
          child: navBar,
        ),
      ),
    );
  }

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
