import 'package:flutter/material.dart';

import '../../../../design_system/design_system.dart';
import '../../../markets/presentation/widgets/bundle_performance_chart_module.dart';
import '../../application/assistance_deep_link_resolver.dart';
import '../../data/chat_api.dart';

/// Carte « bundle detail » embarquée dans une bulle assistant — Phase 2
/// wiki v1.4. Réplique stricte de la **partie haute** de la page détail
/// bundle (`BundleInstrumentDetailHero` / `LayoutPageInstrumentDetail`)
/// dans une bulle chat.
///
/// L'agent `product` déclenche un embed `bundle_detail_card` via le tool
/// `show_bundle_detail` quand le client cible UN bundle nommé (ex.
/// *« parle-moi du bundle TOP5 »*). Le payload backend contient :
///
///   - `id` (UUID `pe_product_definitions`)
///   - `product_code` (ex. `TOP5`) — clé pour le chart
///   - `name`, `description`, `risk_label`, `base_currency`
///   - `allocations` (liste de `{symbol, instrument_name, weight}`)
///   - `actions` : 2 deep-links whitelisted
///     - `view_bundle_detail` → bouton « Voir détail » → fiche produit
///     - `invest_bundle` → bouton « Investir » → flow d'investissement
///
/// Différence clé avec [CryptoBundlesCardEmbed] : on affiche **UN seul
/// bundle** en mode fiche détaillée (vs slider multi-cards).
///
/// Composition visuelle (haut → bas) :
///   1. Tag « Crypto Bundle » (`CategoryBadge`)
///   2. Avatar empilé des allocations (`BundleTickerAvatarRow`)
///   3. Titre du bundle + description courte
///   4. Performance row (chips perf % + libellé période — alimentée par
///      `BundlePerformanceChartModule.onHeroMetricsChanged`)
///   5. Chart de performance bord-à-bord du module (réplique exacte
///      via `BundlePerformanceChartModule(embedInstrumentHero: true)`).
///   6. CTAs « Voir détail » + « Investir » sous le chart
///
/// Encapsulé dans un module blanc bulle assistant (radius bubble +
/// shadow), chart bord-à-bord du module (pas de l'écran).
class BundleDetailCardEmbed extends StatefulWidget {
  const BundleDetailCardEmbed({
    super.key,
    required this.bundle,
  });

  final AssistanceCryptoBundleItem bundle;

  @override
  State<BundleDetailCardEmbed> createState() => _BundleDetailCardEmbedState();
}

class _BundleDetailCardEmbedState extends State<BundleDetailCardEmbed> {
  BundleChartHeroMetrics? _metrics;

  /// Allocations triées par poids croissant (= même tri que
  /// `BundleAllocationAvatarStack` côté markets pour cohérence visuelle).
  List<String> get _orderedSymbols {
    final allocs = List<AssistanceBundleAllocation>.from(widget.bundle.allocations);
    allocs.sort((a, b) => a.weight.compareTo(b.weight));
    return allocs
        .map((a) => a.symbol.trim().toUpperCase())
        .where((s) => s.isNotEmpty)
        .toList();
  }

  Widget? _buildPerformanceRow() {
    final m = _metrics;
    if (m == null || !m.hasPoints) return null;
    final isPositive = m.performancePct >= 0;
    final perfColor = isPositive
        ? AppColors.semanticPositive
        : AppColors.semanticNegative;
    final sign = isPositive ? '+' : '-';
    return InstrumentDetailHeroPerformanceRow(
      // Pas d'abs en devise (les bundles n'ont pas de prix unitaire) —
      // seul le % est pertinent. C'est aussi ce que fait la page détail
      // bundle (`BundleInstrumentDetailHero._buildPerformanceRow`).
      absChipText: null,
      percentChipText: '$sign${m.performancePct.abs().toStringAsFixed(2)} %',
      periodLabel: m.periodCaption,
      percentColor: perfColor,
      percentIsPositive: isPositive,
    );
  }

  Widget _buildHeader() {
    final symbols = _orderedSymbols;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        const CategoryBadge(
          label: 'Crypto Bundle',
          dotColor: AppColors.accent,
        ),
        const SizedBox(height: AppSpacing.s2),
        if (symbols.isNotEmpty) ...[
          BundleTickerAvatarRow(orderedSymbols: symbols),
          const SizedBox(height: AppSpacing.sm),
        ],
        Text(
          widget.bundle.name,
          style: AppTypography.headerTertiary.copyWith(
            color: AppColors.textPrimary,
          ),
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
        ),
        if ((widget.bundle.description ?? '').trim().isNotEmpty) ...[
          const SizedBox(height: AppSpacing.s1),
          Text(
            widget.bundle.description!.trim(),
            style: AppTypography.bodySmall.copyWith(
              color: AppColors.textSecondary,
            ),
            maxLines: 3,
            overflow: TextOverflow.ellipsis,
          ),
        ],
        const SizedBox(height: AppSpacing.s2),
        Builder(
          builder: (_) {
            final perf = _buildPerformanceRow();
            return perf ?? const SizedBox.shrink();
          },
        ),
      ],
    );
  }

  Widget _buildChart(double containerWidth) {
    return BundlePerformanceChartModule(
      productCode: widget.bundle.productCode,
      embedInstrumentHero: true,
      chartContainerWidth: containerWidth,
      onHeroMetricsChanged: (m) {
        if (!mounted) return;
        setState(() => _metrics = m);
      },
    );
  }

  Widget _buildCtas(BuildContext context) {
    final view = widget.bundle.viewDetailDeepLink;
    final invest = widget.bundle.investDeepLink;
    final children = <Widget>[];
    if (view != null && view.isNotEmpty) {
      children.add(
        AppPrimaryButton(
          label: 'Voir détail',
          size: AppPrimaryButtonSize.medium,
          variant: AppPrimaryButtonVariant.secondary,
          horizontalPadding: AppSpacing.s4,
          leading: const Icon(Icons.arrow_outward_rounded, size: 20),
          onPressed: () => _resolveDeepLink(context, view),
        ),
      );
    }
    if (invest != null && invest.isNotEmpty) {
      children.add(
        AppPrimaryButton(
          label: 'Investir',
          size: AppPrimaryButtonSize.medium,
          variant: AppPrimaryButtonVariant.primary,
          horizontalPadding: AppSpacing.s4,
          leading: const Icon(Icons.arrow_upward_rounded, size: 20),
          onPressed: () => _resolveDeepLink(context, invest),
        ),
      );
    }
    if (children.isEmpty) return const SizedBox.shrink();
    return InstrumentDetailHeroCtaRow(children: children);
  }

  Future<void> _resolveDeepLink(BuildContext context, String deepLink) async {
    if (deepLink.isEmpty) return;
    await AssistanceDeepLinkResolver.resolve(context, deepLink);
  }

  @override
  Widget build(BuildContext context) {
    return _CardShell(
      child: LayoutBuilder(
        builder: (context, constraints) {
          final containerWidth = constraints.maxWidth;
          return Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            mainAxisSize: MainAxisSize.min,
            children: [
              Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: AppSpacing.lg,
                ),
                child: _buildHeader(),
              ),
              const SizedBox(height: AppSpacing.md),
              _buildChart(containerWidth),
              const SizedBox(height: AppSpacing.md),
              Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: AppSpacing.lg,
                ),
                child: _buildCtas(context),
              ),
            ],
          );
        },
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────
// Card shell — coque blanche bulle assistant (radius bubble, shadow)
// ─────────────────────────────────────────────────────────────────────

/// Coque spécifique à `BundleDetailCardEmbed` : pas de padding
/// horizontal (le chart bord-à-bord). Le header et les CTAs
/// gèrent leur propre `Padding(horizontal: lg)`. Mêmes propriétés
/// visuelles que `InstrumentDetailCardEmbed._CardShell` pour
/// cohérence inter-embeds.
class _CardShell extends StatelessWidget {
  const _CardShell({required this.child});
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(vertical: AppSpacing.md),
      clipBehavior: Clip.antiAlias,
      decoration: const BoxDecoration(
        color: AppColors.cardBackground,
        borderRadius: BorderRadius.only(
          topLeft: Radius.zero,
          topRight: Radius.circular(AppRadius.bubble),
          bottomLeft: Radius.circular(AppRadius.bubble),
          bottomRight: Radius.circular(AppRadius.bubble),
        ),
        boxShadow: AppShadow.defaultShadowList,
      ),
      child: child,
    );
  }
}
