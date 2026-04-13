import 'package:flutter/material.dart';

import '../../../../core/config.dart';
import '../../../../design_system/design_system.dart';
import '../../data/product_catalog_api.dart';
import 'bundle_allocation_avatar_stack.dart';
import 'bundle_performance_chart_module.dart';
import 'chart_asset_module.dart';

/// Shell détail produit **bundle** : même gabarit que le détail instrument
/// ([LayoutPageInstrumentDetail]) — ligne perf % dans le header, courbe en hero.
class BundleInstrumentDetailHero extends StatefulWidget {
  const BundleInstrumentDetailHero({
    super.key,
    required this.productCode,
    required this.title,
    required this.leadingType,
    required this.onLeadingTap,
    required this.navBarActions,
    required this.content,
    /// Champ `subtitle` du module TitlePage (CMS), sous le titre bundle.
    this.titleDescription,
    /// Allocations cible (API produit) : empilement d’avatars à gauche du titre.
    this.bundleAllocations,
    /// Image CMS si pas d’[bundleAllocations].
    this.heroImageUrl,
    this.footerContent,
    this.fixedBottomCta,
    this.onRefresh,
    this.onInvestTap,
  });

  final String productCode;
  final String title;
  final AppTopNavBarLeading leadingType;
  final VoidCallback onLeadingTap;
  final List<AppTopNavBarAction> navBarActions;
  final List<Widget> content;
  final String? titleDescription;
  final List<ProductAllocationSummary>? bundleAllocations;
  final String? heroImageUrl;
  final Widget? footerContent;
  final ({String label, VoidCallback onTap})? fixedBottomCta;
  final Future<void> Function()? onRefresh;
  final VoidCallback? onInvestTap;

  /// Image CMS (header) — même résolution que les médias catalogue.
  static Widget? titleLeadingFromCmsUrl(String? rawUrl) {
    final resolved = Config.resolveLogoUrl(rawUrl?.trim());
    if (resolved == null || resolved.isEmpty) return null;
    return SizedBox(
      width: 24,
      height: 24,
      child: ClipOval(
        child: Image.network(
          resolved,
          fit: BoxFit.cover,
          errorBuilder: (_, __, ___) => ColoredBox(
            color: AppColors.textPrimary.withValues(alpha: 0.12),
            child: Icon(
              Icons.layers_outlined,
              size: 14,
              color: AppColors.textSecondary.withValues(alpha: 0.8),
            ),
          ),
        ),
      ),
    );
  }

  /// Avatars empilés (allocations triées) ou image CMS.
  static Widget? buildTitleLeading({
    List<ProductAllocationSummary>? allocations,
    String? cmsHeroImageUrl,
  }) {
    if (allocations != null && allocations.isNotEmpty) {
      return BundleAllocationAvatarStack(allocations: allocations);
    }
    return titleLeadingFromCmsUrl(cmsHeroImageUrl);
  }

  @override
  State<BundleInstrumentDetailHero> createState() =>
      _BundleInstrumentDetailHeroState();
}

class _BundleInstrumentDetailHeroState extends State<BundleInstrumentDetailHero> {
  BundleChartHeroMetrics? _metrics;

  @override
  Widget build(BuildContext context) {
    final code = widget.productCode.trim();
    final hasChart = code.isNotEmpty;
    final title = widget.title.trim().isEmpty ? 'Crypto Bundle' : widget.title.trim();

    final chart = hasChart
        ? BundlePerformanceChartModule(
            productCode: code,
            embedInstrumentHero: true,
            onHeroMetricsChanged: (m) {
              if (!mounted) return;
              setState(() => _metrics = m);
            },
          )
        : null;

    Widget? heroActionsSlot;
    if (hasChart) {
      final perf = _buildPerformanceRow();
      if (perf != null) {
        heroActionsSlot = perf;
      } else if (widget.onInvestTap != null) {
        heroActionsSlot = const SizedBox.shrink();
      }
    }

    return LayoutPageInstrumentDetail(
      titleLeading: BundleInstrumentDetailHero.buildTitleLeading(
        allocations: widget.bundleAllocations,
        cmsHeroImageUrl: widget.heroImageUrl,
      ),
      title: title,
      titleDescription: widget.titleDescription,
      categoryBadges: const [
        ArticleCategoryBadgeData(
          label: 'Crypto Bundle',
          dotColor: AppColors.accent,
        ),
      ],
      heroActions: heroActionsSlot,
      heroFullBleed: chart,
      showChart: chart != null,
      heroChartAreaEstimatedHeight: ChartAssetModule.instrumentDetailEstimatedHeightPx,
      heroActionsBelowFullBleed: widget.onInvestTap == null
          ? null
          : InstrumentDetailHeroCtaRow(
              children: [
                AppPrimaryButton(
                  label: 'Investir',
                  size: AppPrimaryButtonSize.medium,
                  variant: AppPrimaryButtonVariant.primary,
                  horizontalPadding: AppSpacing.s4,
                  leading: const Icon(Icons.trending_up_rounded, size: 20),
                  onPressed: widget.onInvestTap,
                ),
              ],
            ),
      leadingType: widget.leadingType,
      onLeadingTap: widget.onLeadingTap,
      navBarActions: widget.navBarActions,
      content: widget.content,
      footerContent: widget.footerContent,
      fixedBottomCta: widget.fixedBottomCta,
      onRefresh: widget.onRefresh,
    );
  }

  Widget? _buildPerformanceRow() {
    final m = _metrics;
    if (m == null || !m.hasPoints) return null;
    final perfColor = m.performancePct >= 0
        ? AppColors.semanticPositive
        : AppColors.semanticNegative;
    final isPos = m.performancePct >= 0;
    final signPct = isPos ? '+' : '-';
    return InstrumentDetailHeroPerformanceRow(
      percentChipText: '$signPct${m.performancePct.abs().toStringAsFixed(2)} %',
      periodLabel: m.periodCaption,
      percentColor: perfColor,
      percentIsPositive: isPos,
    );
  }
}
