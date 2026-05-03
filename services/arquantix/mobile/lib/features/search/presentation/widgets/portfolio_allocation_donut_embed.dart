import 'package:flutter/material.dart';

import '../../../../design_system/design_system.dart';
import '../../../news/presentation/markdown/article_paragraph_markdown.dart';
import '../../data/chat_api.dart';

/// Carte « allocation portefeuille » (donut chart) embarquée dans une
/// bulle assistant.
///
/// Phase 2c.5 Lot 3 — l'agent `compliance.transactional` produit un
/// embed via le tool `stats_portfolio_allocation`. Le serveur envoie
/// au client :
///
///   - ``currency`` (`EUR`)
///   - ``total_value`` (NAV total en €)
///   - ``summary`` (récap textuel composé serveur — chaleureux)
///   - ``slices`` : liste de `{key, label, value, percentage}`
///
/// Ce widget :
///   1. rend le ``summary`` markdown en haut de la carte (cohérent
///      avec [TransactionDetailEmbed]) ;
///   2. rend [DonutsChartBig] en dessous, qui affiche le donut + la
///      légende deux colonnes ;
///   3. ne fait **aucun fetch réseau** : toute la donnée nécessaire
///      est déjà dans l'embed (la responsabilité de calcul reste
///      côté serveur, le client se contente de rendre).
///
/// Cohérence visuelle : enveloppe [_CardShell] alignée avec celle de
/// [TransactionDetailEmbed] (même radius, même couleur, même shadow)
/// pour qu'une bulle « stats portfolio allocation » et une bulle
/// « détail transaction » aient une identité visuelle commune.
class PortfolioAllocationDonutEmbed extends StatelessWidget {
  const PortfolioAllocationDonutEmbed({
    super.key,
    required this.slices,
    required this.summary,
    this.currency = 'EUR',
    this.totalValue,
  });

  /// Slices d'allocation (au moins 1 slice non-nulle attendue ; si
  /// vide, on affiche un message texte).
  final List<AssistanceAllocationSlice> slices;

  /// Récap textuel composé serveur. Toujours présent en happy path.
  /// `null` (rétro-compat) → on n'affiche pas de paragraphe au-dessus
  /// du donut.
  final String? summary;

  /// Devise affichée dans la légende. Aujourd'hui le serveur envoie
  /// toujours `EUR`, mais on prépare le multi-devise.
  final String currency;

  /// NAV total — purement informatif côté UI, le donut s'auto-suffit.
  final double? totalValue;

  @override
  Widget build(BuildContext context) {
    if (slices.isEmpty) {
      return _CardShell(
        child: ArticleParagraphMarkdown(
          text: summary?.trim().isNotEmpty == true
              ? summary!
              : '_Ton portefeuille est vide pour l\'instant — aucune '
                  'allocation à afficher._',
          baseStyle: AppTypography.paragraph,
          blockSpacing: AppSpacing.sm,
        ),
      );
    }

    final donutSlices = slices
        .map(
          (s) => DonutsChartSlice(
            label: s.label,
            percentage: s.percentage,
          ),
        )
        .toList();

    return _CardShell(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          if (summary != null && summary!.trim().isNotEmpty) ...[
            ArticleParagraphMarkdown(
              text: summary!.trim(),
              baseStyle: AppTypography.paragraph,
              blockSpacing: AppSpacing.sm,
            ),
            const SizedBox(height: AppSpacing.md),
          ],
          DonutsChartBig(
            slices: donutSlices,
            sliceColors: _resolveColors(donutSlices.length),
          ),
        ],
      ),
    );
  }

  /// Palette par défaut pour les 3 slices macro (fiat / direct /
  /// bundles). Si la quantité de slices change un jour (ex. on
  /// passera à un niveau d'instrument), [DonutsChartBig] tombera
  /// sur sa palette interne — pas de crash.
  List<Color>? _resolveColors(int count) {
    const palette = <Color>[
      Color(0xFF3B82F6), // bleu — Cash
      Color(0xFFF59E0B), // orange — Crypto direct
      Color(0xFF10B981), // vert  — Bundles
      Color(0xFF8B5CF6), // violet (slot 4)
      Color(0xFFEF4444), // rouge (slot 5)
    ];
    if (count == 0) return null;
    if (count > palette.length) return null;
    return palette.sublist(0, count);
  }
}

// ─────────────────────────────────────────────────────────────────────
// Card shell — aligné avec TransactionDetailEmbed pour cohérence
// ─────────────────────────────────────────────────────────────────────

class _CardShell extends StatelessWidget {
  const _CardShell({required this.child});
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.lg,
        vertical: AppSpacing.md,
      ),
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
