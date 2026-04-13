import 'package:flutter/material.dart';

import '../../../../core/currency_formatter.dart';
import '../../../../design_system/design_system.dart';
import '../../data/trigger_orders_api.dart';
import '../../domain/models/trigger_order.dart';
import 'create_order_bottom_sheet.dart';

class OrdersListScreen extends StatefulWidget {
  final String asset;
  final double? currentPrice;

  const OrdersListScreen({
    super.key,
    required this.asset,
    this.currentPrice,
  });

  @override
  State<OrdersListScreen> createState() => _OrdersListScreenState();
}

class _OrdersListScreenState extends State<OrdersListScreen> {
  final _api = TriggerOrdersApi();
  List<TriggerOrder>? _orders;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    final orders = await _api.fetchOrders(asset: widget.asset);
    if (!mounted) return;
    setState(() {
      _orders = orders;
      _loading = false;
    });
  }

  Future<void> _createOrder() async {
    final result = await CreateOrderBottomSheet.show(
      context,
      asset: widget.asset,
      currentPrice: widget.currentPrice,
    );
    if (result != null) _load();
  }

  Future<void> _cancel(TriggerOrder order) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppColors.cardBackground,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: const Text('Annuler l\'ordre ?'),
        content: Text(
          '${order.typeLabel} ${widget.asset} @ ${CurrencyFormatter.priceUsd(order.triggerPrice)}',
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Non')),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Annuler l\'ordre', style: TextStyle(color: Color(0xFFDC2626))),
          ),
        ],
      ),
    );
    if (confirm == true) {
      await _api.cancelOrder(order.id);
      _load();
    }
  }

  @override
  Widget build(BuildContext context) {
    final active = _orders?.where((o) => o.isActive).toList() ?? [];
    final past = _orders?.where((o) => !o.isActive).toList() ?? [];

    return PageSimpleNavBarTopTitlePageContent(
      pageTitle: 'Ordres ${widget.asset}',
      onRefresh: _load,
      navBarActions: [
        AppTopNavBarAction(
          icon: Icons.add_rounded,
          onPressed: _createOrder,
        ),
      ],
      content: [
        if (_loading)
          const Padding(
            padding: EdgeInsets.all(AppSpacing.xl),
            child: Center(child: CircularProgressIndicator()),
          )
        else if (_orders == null || _orders!.isEmpty)
          _EmptyState(asset: widget.asset, onCreateOrder: _createOrder)
        else ...[
          if (active.isNotEmpty) ...[
            const _SectionLabel(text: 'Actifs'),
            ...active.map((o) => _OrderCard(
                  order: o,
                  currentPrice: widget.currentPrice,
                  onCancel: () => _cancel(o),
                )),
          ],
          if (past.isNotEmpty) ...[
            const _SectionLabel(text: 'Historique'),
            ...past.map((o) => _OrderCard(order: o)),
          ],
        ],
      ],
    );
  }
}

class _EmptyState extends StatelessWidget {
  final String asset;
  final VoidCallback onCreateOrder;
  const _EmptyState({required this.asset, required this.onCreateOrder});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 60, horizontal: AppSpacing.xl),
      child: Column(
        children: [
          Container(
            width: 64,
            height: 64,
            decoration: BoxDecoration(
              color: AppColors.pageBackground,
              borderRadius: BorderRadius.circular(20),
            ),
            child: Icon(Icons.swap_vert_rounded, size: 32, color: AppColors.textSecondary.withValues(alpha: 0.4)),
          ),
          const SizedBox(height: AppSpacing.lg),
          Text(
            'Aucun ordre $asset',
            style: AppTypography.sectionTitle.copyWith(fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: AppSpacing.sm),
          Text(
            'Créez un ordre limite ou stop pour acheter ou vendre $asset automatiquement.',
            textAlign: TextAlign.center,
            style: AppTypography.bodySmall.copyWith(color: AppColors.textSecondary, height: 1.4),
          ),
          const SizedBox(height: AppSpacing.xl),
          FilledButton.icon(
            onPressed: onCreateOrder,
            icon: const Icon(Icons.add_rounded, size: 18),
            label: const Text('Créer un ordre'),
            style: FilledButton.styleFrom(
              backgroundColor: AppColors.textPrimary,
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
            ),
          ),
        ],
      ),
    );
  }
}

class _SectionLabel extends StatelessWidget {
  final String text;
  const _SectionLabel({required this.text});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(top: AppSpacing.lg, bottom: AppSpacing.sm),
      child: Text(
        text.toUpperCase(),
        style: AppTypography.labelSmall.copyWith(
          color: AppColors.textSecondary,
          fontWeight: FontWeight.w600,
          letterSpacing: 0.8,
        ),
      ),
    );
  }
}

class _OrderCard extends StatelessWidget {
  final TriggerOrder order;
  final double? currentPrice;
  final VoidCallback? onCancel;

  const _OrderCard({required this.order, this.currentPrice, this.onCancel});

  static const _greenColor = Color(0xFF16A34A);
  static const _redColor = Color(0xFFDC2626);
  static const _orangeColor = Color(0xFFEA580C);
  static const _blueColor = Color(0xFF2563EB);

  @override
  Widget build(BuildContext context) {
    final isActive = order.isActive;
    final isBuy = order.isBuy;
    final sideColor = isBuy ? _greenColor : _redColor;
    final statusColor = isActive ? sideColor : AppColors.textSecondary;
    final distPct = order.distancePercent(currentPrice);

    return Container(
      margin: const EdgeInsets.only(bottom: AppSpacing.sm),
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: AppSpacing.md),
      decoration: BoxDecoration(
        color: AppColors.cardBackground,
        borderRadius: BorderRadius.circular(16),
        border: isActive ? Border.all(color: sideColor.withValues(alpha: 0.15)) : null,
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.04),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Row(
        children: [
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: statusColor.withValues(alpha: isActive ? 0.1 : 0.06),
              borderRadius: BorderRadius.circular(13),
            ),
            child: Icon(
              isBuy ? Icons.arrow_downward_rounded : Icons.arrow_upward_rounded,
              color: statusColor.withValues(alpha: isActive ? 1.0 : 0.5),
              size: 20,
            ),
          ),
          const SizedBox(width: AppSpacing.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Flexible(
                      child: Text(
                        '${order.typeLabel} @ ${CurrencyFormatter.priceUsd(order.triggerPrice)}',
                        style: AppTypography.bodyMedium.copyWith(
                          fontWeight: FontWeight.w600,
                          color: isActive ? AppColors.textPrimary : AppColors.textSecondary,
                          decoration: !isActive && order.status == 'cancelled' ? TextDecoration.lineThrough : null,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    const SizedBox(width: 6),
                    _StatusBadge(order: order),
                  ],
                ),
                const SizedBox(height: 3),
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        _subtitle(order),
                        style: AppTypography.bodySmall.copyWith(
                          color: AppColors.textSecondary,
                          height: 1.3,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    if (isActive && distPct != null) ...[
                      const SizedBox(width: 8),
                      _DistanceBadge(percent: distPct),
                    ],
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(width: AppSpacing.sm),
          if (isActive && onCancel != null)
            GestureDetector(
              onTap: onCancel,
              child: Container(
                width: 32,
                height: 32,
                decoration: BoxDecoration(
                  color: AppColors.pageBackground,
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Icon(Icons.close_rounded, size: 16, color: AppColors.textSecondary.withValues(alpha: 0.6)),
              ),
            )
          else if (order.isExecuted)
            const Icon(Icons.check_circle_rounded, color: _greenColor, size: 22)
          else if (order.isPartial)
            const Icon(Icons.pie_chart_rounded, color: _orangeColor, size: 22)
          else if (order.isFailed)
            const Icon(Icons.error_rounded, color: _redColor, size: 22)
          else if (order.isPending)
            const Icon(Icons.hourglass_top_rounded, color: _blueColor, size: 22),
        ],
      ),
    );
  }

  String _subtitle(TriggerOrder o) {
    final unit = o.isBuy ? '€' : o.asset;
    final amountLabel = o.isBuy
        ? CurrencyFormatter.fiatEur(o.amount)
        : '${o.amount} ${o.asset}';

    if (o.isExecuted && o.executionPrice != null) {
      return 'Exécuté à ${CurrencyFormatter.priceUsd(o.executionPrice!)} · $amountLabel';
    }
    if (o.isPartial) {
      final filled = o.filledAmount ?? 0;
      final requested = o.amount;
      return 'Partiel : ${CurrencyFormatter.fiatEurRaw(filled)} / ${CurrencyFormatter.fiatEurRaw(requested)} $unit';
    }
    if (o.isFailed) {
      final reason = _humanizeFailure(o.failureReason);
      return 'Échoué : $reason · $amountLabel';
    }
    if (o.isPending) {
      return 'Exécution en cours · $amountLabel';
    }
    if (o.status == 'cancelled') {
      return 'Annulé · $amountLabel';
    }
    final slipLabel = o.slippageBps != null ? ' · Slip max ${(o.slippageBps! / 100).toStringAsFixed(1)}%' : '';
    return '$amountLabel$slipLabel';
  }

  String _humanizeFailure(String? reason) {
    switch (reason) {
      case 'slippage_exceeded':
        return 'Slippage trop élevé';
      case 'price_moved_beyond_safety':
        return 'Prix hors limites';
      case 'zero_fill':
        return 'Aucune exécution';
      case 'all_attempts_failed':
        return 'Tentatives épuisées';
      case 'missing_side_or_amount':
        return 'Paramètres manquants';
      case 'exchange_error':
        return 'Erreur exchange';
      case null:
        return 'Erreur';
      default:
        return reason!;
    }
  }
}

class _StatusBadge extends StatelessWidget {
  final TriggerOrder order;
  const _StatusBadge({required this.order});

  @override
  Widget build(BuildContext context) {
    final (label, color) = _resolve();

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(5),
      ),
      child: Text(
        label,
        style: AppTypography.labelSmall.copyWith(
          color: color,
          fontWeight: FontWeight.w600,
          fontSize: 10,
        ),
      ),
    );
  }

  (String, Color) _resolve() {
    if (order.isExecuted) return ('Exécuté', _OrderCard._greenColor);
    if (order.isPartial) return ('Partiel', _OrderCard._orangeColor);
    if (order.isFailed) return ('Échoué', _OrderCard._redColor);
    if (order.isPending) return ('En cours', _OrderCard._blueColor);
    if (order.status == 'cancelled') return ('Annulé', AppColors.textSecondary);
    return ('Actif', order.isBuy ? _OrderCard._greenColor : _OrderCard._redColor);
  }
}

class _DistanceBadge extends StatelessWidget {
  final double percent;
  const _DistanceBadge({required this.percent});

  @override
  Widget build(BuildContext context) {
    final color = percent >= 0 ? _OrderCard._greenColor : _OrderCard._redColor;
    final sign = percent >= 0 ? '+' : '';
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Text(
        '$sign${percent.toStringAsFixed(1)} %',
        style: AppTypography.labelSmall.copyWith(
          color: color,
          fontWeight: FontWeight.w700,
          fontSize: 10,
        ),
      ),
    );
  }
}
