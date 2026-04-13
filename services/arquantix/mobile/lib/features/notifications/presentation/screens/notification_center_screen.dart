import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../../design_system/design_system.dart';
import '../../../wallet/presentation/screens/transaction_screen.dart';
import '../../data/notifications_api.dart';
import '../../domain/models/app_notification.dart';

/// Notification center backed by real API data.
class NotificationCenterScreen extends StatefulWidget {
  const NotificationCenterScreen({super.key});

  @override
  State<NotificationCenterScreen> createState() => _NotificationCenterScreenState();
}

class _NotificationCenterScreenState extends State<NotificationCenterScreen> {
  final _api = NotificationsApi();
  List<AppNotification>? _notifications;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    final result = await _api.fetchNotifications(limit: 100);
    if (!mounted) return;
    setState(() {
      _notifications = result.items;
      _loading = false;
    });
  }

  Future<void> _markAllRead() async {
    await _api.markAllRead();
    _load();
  }

  Future<void> _markRead(AppNotification notif) async {
    if (!notif.isRead) {
      await _api.markRead(notif.id);
      _load();
    }
  }

  void _navigateToTransaction(AppNotification notif) {
    _markRead(notif);
    final orderId = notif.payload?['order_id'] as String?;
    if (orderId == null || orderId.isEmpty) return;
    final side = notif.payload?['side'] as String?;
    Navigator.of(context).push(MaterialPageRoute(
      builder: (_) => TransactionScreen(
        transactionId: orderId,
        merchant: notif.title,
        dateTime: DateFormat('dd/MM/yyyy à HH:mm').format(notif.createdAt.toLocal()),
        amount: '',
        icon: side == 'sell' ? Icons.arrow_upward_rounded : Icons.arrow_downward_rounded,
        iconColor: side == 'sell' ? const Color(0xFFDC2626) : const Color(0xFF16A34A),
      ),
    ));
  }

  void _openDetail(AppNotification notif) {
    _markRead(notif);

    if (notif.type == 'order_executed') {
      _navigateToTransaction(notif);
      return;
    }

    showModalBottomSheet(
      context: context,
      backgroundColor: AppColors.cardBackground,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (_) => _NotificationDetailSheet(notif: notif),
    );
  }

  @override
  Widget build(BuildContext context) {
    final unread = _notifications?.where((n) => !n.isRead).length ?? 0;
    final grouped = _groupByDate(_notifications ?? []);

    return PageSimpleNavBarTopTitlePageContent(
      pageTitle: 'Boîte de réception',
      onRefresh: _load,
      navBarActions: [
        if (unread > 0)
          AppTopNavBarAction(
            icon: Icons.done_all_rounded,
            onPressed: _markAllRead,
          ),
      ],
      content: [
        if (_loading)
          const Center(
            child: Padding(
              padding: EdgeInsets.all(AppSpacing.xl),
              child: CircularProgressIndicator(),
            ),
          )
        else if (_notifications == null || _notifications!.isEmpty)
          Padding(
            padding: const EdgeInsets.all(AppSpacing.xl),
            child: Center(
              child: Column(
                children: [
                  Icon(
                    Icons.inbox_rounded,
                    size: 48,
                    color: AppColors.textSecondary.withValues(alpha: 0.5),
                  ),
                  const SizedBox(height: AppSpacing.md),
                  Text(
                    'Aucune notification',
                    style: AppTypography.bodyMedium.copyWith(
                      color: AppColors.textSecondary,
                    ),
                  ),
                ],
              ),
            ),
          )
        else
          ...grouped.entries.map(
            (entry) => Padding(
              padding: const EdgeInsets.only(bottom: AppSpacing.xl),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    entry.key,
                    style: AppTypography.title2.copyWith(
                      color: AppColors.textPrimary,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: AppSpacing.md),
                  ...entry.value.map(
                    (notif) => Padding(
                      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
                      child: _NotificationCard(
                        notif: notif,
                        onTap: () => _openDetail(notif),
                        onDetailsTap: notif.type == 'order_executed'
                            ? () => _navigateToTransaction(notif)
                            : null,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
      ],
    );
  }

  Map<String, List<AppNotification>> _groupByDate(List<AppNotification> items) {
    final dateFmt = DateFormat('d MMMM', 'fr_FR');
    final map = <String, List<AppNotification>>{};
    for (final n in items) {
      final label = dateFmt.format(n.createdAt.toLocal());
      (map[label] ??= []).add(n);
    }
    return map;
  }
}

class _NotificationCard extends StatelessWidget {
  final AppNotification notif;
  final VoidCallback onTap;
  final VoidCallback? onDetailsTap;

  const _NotificationCard({
    required this.notif,
    required this.onTap,
    this.onDetailsTap,
  });

  static const _greenColor = Color(0xFF16A34A);

  bool get _isOrderExecuted => notif.type == 'order_executed';

  IconData get _icon {
    switch (notif.type) {
      case 'price_alert':
        return Icons.notifications_active_rounded;
      case 'order_executed':
        return Icons.check_circle_rounded;
      default:
        return Icons.info_outline_rounded;
    }
  }

  Color get _iconColor =>
      _isOrderExecuted ? _greenColor : AppColors.textPrimary;

  Color get _iconBgColor => _isOrderExecuted
      ? _greenColor.withValues(alpha: 0.1)
      : AppColors.textPrimary.withValues(alpha: 0.08);

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.md,
          vertical: AppSpacing.md,
        ),
        decoration: BoxDecoration(
          color: AppColors.cardBackground,
          borderRadius: BorderRadius.circular(16),
          border: _isOrderExecuted
              ? Border.all(color: _greenColor.withValues(alpha: 0.15))
              : null,
          boxShadow: [
            BoxShadow(
              color: AppColors.textPrimary.withValues(alpha: 0.04),
              blurRadius: 6,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(
                color: _iconBgColor,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(_icon, color: _iconColor, size: 20),
            ),
            const SizedBox(width: AppSpacing.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    notif.title,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: AppTypography.titleSmall.copyWith(
                      fontWeight: notif.isRead ? FontWeight.w500 : FontWeight.w700,
                      color: AppColors.textPrimary,
                    ),
                  ),
                  if (notif.body != null) ...[
                    const SizedBox(height: 4),
                    Text(
                      notif.body!,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: AppTypography.paragraph.copyWith(
                        color: AppColors.textSecondary,
                        fontSize: 13,
                        height: 1.3,
                      ),
                    ),
                  ],
                  if (_isOrderExecuted && onDetailsTap != null) ...[
                    const SizedBox(height: 8),
                    GestureDetector(
                      onTap: onDetailsTap,
                      child: Text(
                        'Voir les détails →',
                        style: AppTypography.label.copyWith(
                          color: _greenColor,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            ),
            const SizedBox(width: AppSpacing.sm),
            if (!notif.isRead)
              Padding(
                padding: const EdgeInsets.only(top: 6),
                child: Container(
                  width: 8,
                  height: 8,
                  decoration: const BoxDecoration(
                    color: Colors.blue,
                    shape: BoxShape.circle,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _NotificationDetailSheet extends StatelessWidget {
  final AppNotification notif;

  const _NotificationDetailSheet({required this.notif});

  @override
  Widget build(BuildContext context) {
    final timeFmt = DateFormat('dd/MM/yyyy à HH:mm');
    return Padding(
      padding: const EdgeInsets.all(AppSpacing.lg),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Center(
            child: Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: AppColors.textSecondary.withValues(alpha: 0.3),
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          const SizedBox(height: AppSpacing.lg),
          Text(
            notif.title,
            style: AppTypography.modalTitle,
          ),
          if (notif.body != null) ...[
            const SizedBox(height: AppSpacing.md),
            Text(
              notif.body!,
              style: AppTypography.paragraph.copyWith(
                color: AppColors.textSecondary,
                height: 1.4,
              ),
            ),
          ],
          const SizedBox(height: AppSpacing.lg),
          Text(
            timeFmt.format(notif.createdAt.toLocal()),
            style: AppTypography.meta,
          ),
          const SizedBox(height: AppSpacing.xl),
        ],
      ),
    );
  }
}
