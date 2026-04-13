import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../../core/currency_formatter.dart';
import '../../../../design_system/design_system.dart';
import '../../data/price_alerts_api.dart';
import '../../domain/models/price_alert.dart';
import 'create_alert_bottom_sheet.dart';

final _fmtDate = DateFormat('dd MMM yyyy, HH:mm');

class AlertsListScreen extends StatefulWidget {
  final String asset;
  final double? currentPrice;

  const AlertsListScreen({
    super.key,
    required this.asset,
    this.currentPrice,
  });

  @override
  State<AlertsListScreen> createState() => _AlertsListScreenState();
}

class _AlertsListScreenState extends State<AlertsListScreen> {
  final _api = PriceAlertsApi();
  List<PriceAlert>? _alerts;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    final alerts = await _api.fetchAlerts(asset: widget.asset);
    if (!mounted) return;
    setState(() {
      _alerts = alerts;
      _loading = false;
    });
  }

  Future<void> _createAlert() async {
    final result = await CreateAlertBottomSheet.show(
      context,
      asset: widget.asset,
      currentPrice: widget.currentPrice,
    );
    if (result != null) _load();
  }

  Future<void> _removeAll() async {
    final alerts = _alerts;
    if (alerts == null || alerts.isEmpty) return;
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppColors.cardBackground,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: const Text('Tout supprimer ?'),
        content: Text('${alerts.length} alerte(s) ${widget.asset} seront définitivement supprimées.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Annuler')),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Supprimer', style: TextStyle(color: Color(0xFFDC2626))),
          ),
        ],
      ),
    );
    if (confirm != true) return;
    await _api.deleteAllAlerts(asset: widget.asset);
    _load();
  }

  Future<void> _cancel(PriceAlert alert) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: AppColors.cardBackground,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: const Text('Supprimer l\'alerte ?'),
        content: Text(
          '${alert.asset} ${alert.isUp ? ">" : "<"} ${CurrencyFormatter.price(alert.targetPrice)}',
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Annuler')),
          TextButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Supprimer', style: TextStyle(color: Color(0xFFDC2626))),
          ),
        ],
      ),
    );
    if (confirm == true) {
      await _api.cancelAlert(alert.id);
      _load();
    }
  }

  @override
  Widget build(BuildContext context) {
    final active = _alerts?.where((a) => a.isActive).toList() ?? [];
    final past = _alerts?.where((a) => !a.isActive).toList() ?? [];

    return PageSimpleNavBarTopTitlePageContent(
      pageTitle: 'Alertes ${widget.asset}',
      navBarActions: [
        AppTopNavBarAction(
          icon: Icons.add_rounded,
          onPressed: _createAlert,
        ),
      ],
      content: [
        if (!_loading && _alerts != null && _alerts!.isNotEmpty)
          Align(
            alignment: Alignment.centerLeft,
            child: Padding(
              padding: const EdgeInsets.only(bottom: AppSpacing.sm),
              child: GestureDetector(
                onTap: _removeAll,
                child: Text(
                  'Tout supprimer',
                  style: AppTypography.bodySmall.copyWith(
                    color: AppColors.textSecondary,
                    decoration: TextDecoration.underline,
                  ),
                ),
              ),
            ),
          ),
        if (_loading)
          const Padding(
            padding: EdgeInsets.all(AppSpacing.xl),
            child: Center(child: CircularProgressIndicator()),
          )
        else if (_alerts == null || _alerts!.isEmpty)
          _EmptyState(asset: widget.asset, onCreateAlert: _createAlert)
        else ...[
          if (active.isNotEmpty) ...[
            const _SectionLabel(text: 'Actives'),
            ...active.map((a) => _AlertCard(
                  alert: a,
                  currentPrice: widget.currentPrice,
                  onCancel: () => _cancel(a),
                )),
          ],
          if (past.isNotEmpty) ...[
            const _SectionLabel(text: 'Historique'),
            ...past.map((a) => _AlertCard(alert: a)),
          ],
        ],
      ],
    );
  }
}

class _EmptyState extends StatelessWidget {
  final String asset;
  final VoidCallback onCreateAlert;
  const _EmptyState({required this.asset, required this.onCreateAlert});

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
            child: Icon(Icons.notifications_none_rounded, size: 32, color: AppColors.textSecondary.withValues(alpha: 0.4)),
          ),
          const SizedBox(height: AppSpacing.lg),
          Text(
            'Aucune alerte $asset',
            style: AppTypography.sectionTitle.copyWith(fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: AppSpacing.sm),
          Text(
            'Recevez une notification dès que $asset atteint votre prix cible.',
            textAlign: TextAlign.center,
            style: AppTypography.bodySmall.copyWith(color: AppColors.textSecondary, height: 1.4),
          ),
          const SizedBox(height: AppSpacing.xl),
          FilledButton.icon(
            onPressed: onCreateAlert,
            icon: const Icon(Icons.add_rounded, size: 18),
            label: const Text('Créer une alerte'),
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

class _AlertCard extends StatelessWidget {
  final PriceAlert alert;
  final double? currentPrice;
  final VoidCallback? onCancel;

  const _AlertCard({required this.alert, this.currentPrice, this.onCancel});

  static const _greenColor = Color(0xFF16A34A);
  static const _redColor = Color(0xFFDC2626);

  @override
  Widget build(BuildContext context) {
    final isActive = alert.isActive;
    final isUp = alert.isUp;
    final dirColor = isUp ? _greenColor : _redColor;
    final statusColor = isActive ? dirColor : AppColors.textSecondary;
    final distPct = alert.distancePercent(currentPrice);

    return Container(
      margin: const EdgeInsets.only(bottom: AppSpacing.sm),
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: AppSpacing.md),
      decoration: BoxDecoration(
        color: AppColors.cardBackground,
        borderRadius: BorderRadius.circular(16),
        border: isActive ? Border.all(color: dirColor.withValues(alpha: 0.15)) : null,
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
              isUp ? Icons.arrow_upward_rounded : Icons.arrow_downward_rounded,
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
                        '${isUp ? ">" : "<"} ${CurrencyFormatter.price(alert.targetPrice)}',
                        style: AppTypography.bodyMedium.copyWith(
                          fontWeight: FontWeight.w600,
                          color: isActive ? AppColors.textPrimary : AppColors.textSecondary,
                          decoration: !isActive && !alert.isRecurring ? TextDecoration.lineThrough : null,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    const SizedBox(width: 6),
                    if (alert.isRecurring)
                      const _Badge(label: 'Toujours', color: Color(0xFFEA580C))
                    else
                      _Badge(label: 'Une fois', color: AppColors.textSecondary),
                  ],
                ),
                const SizedBox(height: 3),
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        _subtitle(alert),
                        style: AppTypography.bodySmall.copyWith(
                          color: AppColors.textSecondary,
                          height: 1.3,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    if (isActive && distPct != null) ...[
                      const SizedBox(width: 8),
                      _DistanceBadge(percent: distPct, isUp: isUp),
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
          else if (alert.isTriggered)
            Icon(Icons.check_circle_rounded, color: dirColor, size: 22),
        ],
      ),
    );
  }

  String _subtitle(PriceAlert a) {
    if (a.isTriggered && a.triggeredAt != null) {
      final pricePart = a.triggeredPrice != null ? ' à ${CurrencyFormatter.price(a.triggeredPrice!)}' : '';
      return 'Déclenché le ${_fmtDate.format(a.triggeredAt!.toLocal())}$pricePart';
    }
    if (a.isRecurring && a.triggerCount > 0) {
      final last = a.triggeredAt != null ? _fmtDate.format(a.triggeredAt!.toLocal()) : '—';
      return '${a.triggerCount}x déclenché · Dernier : $last';
    }
    return 'Créé le ${_fmtDate.format(a.createdAt.toLocal())}';
  }
}

class _DistanceBadge extends StatelessWidget {
  final double percent;
  final bool isUp;
  const _DistanceBadge({required this.percent, required this.isUp});

  @override
  Widget build(BuildContext context) {
    final color = percent >= 0 ? _AlertCard._greenColor : _AlertCard._redColor;
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

class _Badge extends StatelessWidget {
  final String label;
  final Color color;
  const _Badge({required this.label, required this.color});

  @override
  Widget build(BuildContext context) {
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
}
