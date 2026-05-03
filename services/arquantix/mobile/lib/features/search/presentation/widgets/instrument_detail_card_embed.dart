import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../../core/config.dart';
import '../../../../design_system/design_system.dart';
import '../../application/assistance_deep_link_resolver.dart';
import '../../data/chat_api.dart';

/// Carte « instrument » embarquée dans une bulle assistant — Phase 2c.6.
///
/// L'agent `product` (ou `advisor`) déclenche un embed
/// `instrument_detail_card` via le tool `show_instrument_card`. Le
/// serveur envoie au client :
///
///   - `symbol` (ex. `BTC`) + `name` (ex. `Bitcoin`) + `logo_url`
///     (`/media/...`)
///   - `currency` (`EUR` ou fallback `USD`) + `price`
///   - `change_24h_abs` + `change_24h_pct` (peuvent être `null`)
///   - `sparkline_24h` : liste de `double` (closes 5 min sur 24 h)
///   - `actions` : 2 deep-links whitelistés `buy_instrument` +
///     `sell_instrument` (cf. `action_cta_catalog`).
///
/// Différence clé avec [TransactionDetailEmbed] et
/// [PortfolioAllocationDonutEmbed] : ici le LLM peut **écrire un
/// texte explicatif en plus** de la carte (ex. *« Bitcoin est la
/// première cryptomonnaie… »*). La carte joue le rôle de **fiche
/// factuelle complémentaire**, pas de réponse exclusive.
///
/// Cohérence visuelle : enveloppe [_CardShell] alignée avec celle de
/// [TransactionDetailEmbed] / [PortfolioAllocationDonutEmbed] (même
/// radius, même couleur, même shadow).
class InstrumentDetailCardEmbed extends StatelessWidget {
  const InstrumentDetailCardEmbed({
    super.key,
    required this.symbol,
    required this.name,
    required this.currency,
    required this.price,
    required this.actions,
    this.logoUrl,
    this.change24hAbs,
    this.change24hPct,
    this.sparkline = const [],
  });

  final String symbol;
  final String name;
  final String currency;
  final double price;
  final List<AssistanceChoiceOption> actions;
  final String? logoUrl;
  final double? change24hAbs;
  final double? change24hPct;
  final List<double> sparkline;

  @override
  Widget build(BuildContext context) {
    final perfColor = _resolvePerfColor();
    final perfIsPositive = (change24hPct ?? 0) >= 0;

    return _CardShell(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          _buildHeaderRow(),
          const SizedBox(height: AppSpacing.sm),
          _buildPrice(),
          if (change24hAbs != null || change24hPct != null) ...[
            const SizedBox(height: AppSpacing.s2),
            InstrumentDetailHeroPerformanceRow(
              absChipText: _formatChangeAbs(),
              absChipColor: instrumentHeroAbsChipColor(
                changeAbs: change24hAbs,
                changePct: change24hPct,
                perfColor: perfColor,
              ),
              percentChipText: _formatChangePct(),
              periodLabel: '1 jour',
              percentColor: perfColor,
              percentIsPositive: perfIsPositive,
            ),
          ],
          if (actions.isNotEmpty) ...[
            const SizedBox(height: AppSpacing.md),
            _buildActions(context),
          ],
          if (sparkline.length >= 2) ...[
            const SizedBox(height: AppSpacing.md),
            SizedBox(
              height: 96,
              width: double.infinity,
              child: _MiniSparkline(
                values: sparkline,
                lineColor: perfColor,
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildHeaderRow() {
    final logo = _buildLogo();
    return Row(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        if (logo != null) ...[
          logo,
          const SizedBox(width: AppSpacing.s2),
        ],
        Expanded(
          child: Text(
            name,
            style: AppTypography.headerTertiary.copyWith(
              color: AppColors.textPrimary,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ),
      ],
    );
  }

  Widget? _buildLogo() {
    final resolved = Config.resolveLogoUrl(logoUrl);
    if (resolved == null || resolved.isEmpty) return null;
    return ClipRRect(
      borderRadius: BorderRadius.circular(12),
      child: Image.network(
        resolved,
        width: 24,
        height: 24,
        fit: BoxFit.cover,
        errorBuilder: (_, __, ___) => const SizedBox(width: 24, height: 24),
      ),
    );
  }

  Widget _buildPrice() {
    return Text(
      _formatPrice(),
      style: AppTypography.amountPrimary.copyWith(
        color: AppColors.textPrimary,
        inherit: false,
      ),
      maxLines: 1,
      overflow: TextOverflow.ellipsis,
    );
  }

  Widget _buildActions(BuildContext context) {
    final ctas = actions.where((a) => a.hasDeepLink).toList(growable: false);
    if (ctas.isEmpty) return const SizedBox.shrink();
    return InstrumentDetailHeroCtaRow(
      children: [
        for (final action in ctas.take(2))
          _buildCtaButton(context, action),
      ],
    );
  }

  Widget _buildCtaButton(BuildContext context, AssistanceChoiceOption action) {
    final isSell = action.id == 'sell_instrument';
    void onTap() {
      final link = action.deepLink;
      if (link == null || link.isEmpty) return;
      AssistanceDeepLinkResolver.resolve(context, link);
    }

    if (isSell) {
      return AppSecondaryButton(
        label: action.label,
        onPressed: onTap,
        size: AppPrimaryButtonSize.medium,
      );
    }
    return AppPrimaryButton(
      label: action.label,
      onPressed: onTap,
      size: AppPrimaryButtonSize.medium,
    );
  }

  // ──────────────────────────────────────────────────────────────────
  // Formatage
  // ──────────────────────────────────────────────────────────────────

  Color _resolvePerfColor() {
    final pct = change24hPct;
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
      decimalDigits: _decimalsForPrice(price),
    );
    return fmt.format(price);
  }

  String? _formatChangeAbs() {
    final abs = change24hAbs;
    if (abs == null) return null;
    final symbolDisplay = _currencySymbol();
    final sign = abs > 0 ? '+' : (abs < 0 ? '−' : '');
    final fmt = NumberFormat.currency(
      locale: 'fr_FR',
      symbol: symbolDisplay,
      decimalDigits: _decimalsForPrice(abs.abs()),
    );
    return '$sign${fmt.format(abs.abs())}';
  }

  String _formatChangePct() {
    final pct = change24hPct;
    if (pct == null) return '—';
    final sign = pct > 0 ? '+' : (pct < 0 ? '−' : '');
    final formatted = pct.abs().toStringAsFixed(2).replaceAll('.', ',');
    return '$sign$formatted %';
  }

  String _currencySymbol() {
    switch (currency.toUpperCase()) {
      case 'EUR':
        return '€';
      case 'USD':
        return r'$';
      case 'GBP':
        return '£';
      default:
        return ' ${currency.toUpperCase()}';
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

// ─────────────────────────────────────────────────────────────────────
// Mini sparkline — version light du chart pour bulle chat
// ─────────────────────────────────────────────────────────────────────

/// Ligne lissée représentant l'évolution d'un actif sur 24 h. Pas
/// d'axe, pas d'interaction — purement décoratif (les chiffres
/// précis sont dans les puces de performance au-dessus).
class _MiniSparkline extends StatelessWidget {
  const _MiniSparkline({
    required this.values,
    required this.lineColor,
  });

  final List<double> values;
  final Color lineColor;

  @override
  Widget build(BuildContext context) {
    if (values.length < 2) return const SizedBox.shrink();
    return CustomPaint(
      painter: _SparklinePainter(
        values: values,
        lineColor: lineColor,
      ),
    );
  }
}

class _SparklinePainter extends CustomPainter {
  _SparklinePainter({
    required this.values,
    required this.lineColor,
  });

  final List<double> values;
  final Color lineColor;

  @override
  void paint(Canvas canvas, Size size) {
    if (values.length < 2 || size.width <= 0 || size.height <= 0) return;

    var minV = values.first;
    var maxV = values.first;
    for (final v in values) {
      if (v < minV) minV = v;
      if (v > maxV) maxV = v;
    }
    final range = (maxV - minV).abs();
    final span = range == 0 ? 1.0 : range;

    final dx = size.width / (values.length - 1);
    final path = Path();
    final fillPath = Path();

    for (var i = 0; i < values.length; i++) {
      final x = dx * i;
      final ratio = (values[i] - minV) / span;
      // Flip Y axis : plus grande valeur = plus haut (y small).
      final y = size.height - ratio * size.height;
      if (i == 0) {
        path.moveTo(x, y);
        fillPath.moveTo(x, size.height);
        fillPath.lineTo(x, y);
      } else {
        path.lineTo(x, y);
        fillPath.lineTo(x, y);
      }
    }
    fillPath
      ..lineTo(size.width, size.height)
      ..close();

    final fillPaint = Paint()
      ..shader = LinearGradient(
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
        colors: [
          lineColor.withValues(alpha: 0.18),
          lineColor.withValues(alpha: 0.0),
        ],
      ).createShader(Offset.zero & size);
    canvas.drawPath(fillPath, fillPaint);

    final linePaint = Paint()
      ..color = lineColor
      ..strokeWidth = 2.0
      ..style = PaintingStyle.stroke
      ..strokeJoin = StrokeJoin.round
      ..strokeCap = StrokeCap.round;
    canvas.drawPath(path, linePaint);
  }

  @override
  bool shouldRepaint(covariant _SparklinePainter oldDelegate) {
    return oldDelegate.values != values ||
        oldDelegate.lineColor != lineColor;
  }
}

// ─────────────────────────────────────────────────────────────────────
// Card shell — aligné avec TransactionDetailEmbed / PortfolioAllocation
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
