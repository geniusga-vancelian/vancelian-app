import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../../core/config.dart';
import '../../../../design_system/design_system.dart';
import '../../application/assistance_deep_link_resolver.dart';
import '../../data/chat_api.dart';

/// Carte chat « top_movers_crypto » — Phase 2c.7.
///
/// Émise par les agents `market` / `advisor` pour répondre aux
/// questions sur la dynamique du marché crypto 24h. Liste les top
/// hausses / baisses / volumes selon `direction` côté serveur.
///
/// Visuel : enveloppe `_CardShell` cohérent avec les autres embeds.
/// Titre du bloc + 1 à 10 lignes (logo, symbol, prix, variation 24h
/// colorée). Tap → deep-link `view_instrument` → ouverture de la
/// fiche instrument.
///
/// Mode : **complémentaire** (le LLM commente la dynamique au-dessus).
class TopMoversCryptoEmbed extends StatelessWidget {
  const TopMoversCryptoEmbed({
    super.key,
    required this.title,
    required this.items,
    required this.direction,
  });

  final String title;
  final List<AssistanceTopMoverItem> items;

  /// `gainers`, `losers` ou `volume`. Sert au formatage de la métrique
  /// secondaire (perf 24h vs volume).
  final String direction;

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) return const SizedBox.shrink();
    final visible = items.take(10).toList(growable: false);
    return _CardShell(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            title,
            style: AppTypography.headerTertiary.copyWith(
              color: AppColors.textPrimary,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          const SizedBox(height: AppSpacing.sm),
          for (var i = 0; i < visible.length; i++) ...[
            _MoverRow(item: visible[i], direction: direction),
            if (i < visible.length - 1)
              const Padding(
                padding: EdgeInsets.symmetric(
                  vertical: AppSpacing.s2,
                ),
                child: Divider(height: 1),
              ),
          ],
        ],
      ),
    );
  }
}

class _MoverRow extends StatelessWidget {
  const _MoverRow({required this.item, required this.direction});

  final AssistanceTopMoverItem item;
  final String direction;

  @override
  Widget build(BuildContext context) {
    final pct = item.change24hPct;
    final perfColor = _resolvePerfColor(pct);
    return InkWell(
      onTap: item.hasDeepLink
          ? () => AssistanceDeepLinkResolver.resolve(
                context,
                item.deepLink!,
              )
          : null,
      borderRadius: BorderRadius.circular(8),
      child: Padding(
        padding: const EdgeInsets.symmetric(
          vertical: AppSpacing.xs,
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            _buildLogo(),
            const SizedBox(width: AppSpacing.sm),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    item.symbol,
                    style: AppTypography.itemPrimary.copyWith(
                      color: AppColors.textPrimary,
                      fontWeight: FontWeight.w600,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  if (item.name.isNotEmpty &&
                      item.name.toUpperCase() != item.symbol.toUpperCase())
                    Text(
                      item.name,
                      style: AppTypography.itemSupporting.copyWith(
                        color: AppColors.textMuted,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                ],
              ),
            ),
            const SizedBox(width: AppSpacing.s2),
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  _formatPrice(),
                  style: AppTypography.itemPrimary.copyWith(
                    color: AppColors.textPrimary,
                    fontWeight: FontWeight.w500,
                  ),
                  maxLines: 1,
                ),
                Text(
                  _formatSecondaryMetric(),
                  style: AppTypography.itemSupporting.copyWith(
                    color: perfColor,
                    fontWeight: FontWeight.w600,
                  ),
                  maxLines: 1,
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildLogo() {
    final resolved = Config.resolveLogoUrl(item.logoUrl);
    if (resolved == null || resolved.isEmpty) {
      return Container(
        width: 32,
        height: 32,
        decoration: BoxDecoration(
          color: AppColors.pageBackground,
          shape: BoxShape.circle,
        ),
        alignment: Alignment.center,
        child: Text(
          item.symbol.isNotEmpty ? item.symbol.substring(0, 1) : '?',
          style: AppTypography.itemSupporting.copyWith(
            color: AppColors.textMuted,
            fontWeight: FontWeight.w700,
          ),
        ),
      );
    }
    return ClipRRect(
      borderRadius: BorderRadius.circular(16),
      child: Image.network(
        resolved,
        width: 32,
        height: 32,
        fit: BoxFit.cover,
        errorBuilder: (_, __, ___) => Container(
          width: 32,
          height: 32,
          color: AppColors.pageBackground,
        ),
      ),
    );
  }

  Color _resolvePerfColor(double? pct) {
    if (pct == null || pct == 0) return AppColors.textPrimary;
    return pct > 0
        ? AppColors.semanticPositive
        : AppColors.semanticNegative;
  }

  String _formatPrice() {
    final symbolDisplay = _currencySymbol();
    final fmt = NumberFormat.currency(
      locale: 'fr_FR',
      symbol: symbolDisplay,
      decimalDigits: _decimalsForPrice(item.price),
    );
    return fmt.format(item.price);
  }

  String _formatSecondaryMetric() {
    if (direction == 'volume') {
      final v = item.volume24h;
      if (v == null) return '—';
      final compact = NumberFormat.compactCurrency(
        locale: 'fr_FR',
        symbol: _currencySymbol(),
        decimalDigits: 1,
      );
      return compact.format(v);
    }
    final pct = item.change24hPct;
    if (pct == null) return '—';
    final sign = pct > 0 ? '+' : (pct < 0 ? '−' : '');
    final formatted = pct.abs().toStringAsFixed(2).replaceAll('.', ',');
    return '$sign$formatted %';
  }

  String _currencySymbol() {
    switch (item.currency.toUpperCase()) {
      case 'EUR':
        return '€';
      case 'USD':
        return r'$';
      case 'GBP':
        return '£';
      default:
        return ' ${item.currency.toUpperCase()}';
    }
  }

  int _decimalsForPrice(double v) {
    final abs = v.abs();
    if (abs >= 1000) return 0;
    if (abs >= 1) return 2;
    if (abs >= 0.01) return 4;
    return 6;
  }
}

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
