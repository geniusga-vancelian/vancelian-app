import 'package:flutter/material.dart';

import '../../features/wallet/widgets/wallet_header.dart';

class LayoutTopNavBarModule extends StatelessWidget {
  const LayoutTopNavBarModule({
    super.key,
    required this.leftItems,
    required this.rightItems,
    this.onBackTap,
    this.onProfileTap,
    this.onNotificationTap,
    this.onStatisticsTap,
    this.onFavoriteTap,
    this.onShareTap,
    this.profileInitials = 'JA',
    this.showProfileDot = false,
    this.showNotificationDot = false,
    this.backgroundColor = Colors.transparent,
    this.foregroundColor = Colors.white,
    this.useDashboardStyle = true,
  });

  final List<String> leftItems;
  final List<String> rightItems;
  final VoidCallback? onBackTap;
  final VoidCallback? onProfileTap;
  final VoidCallback? onNotificationTap;
  final VoidCallback? onStatisticsTap;
  final VoidCallback? onFavoriteTap;
  final VoidCallback? onShareTap;
  final String profileInitials;
  final bool showProfileDot;
  final bool showNotificationDot;
  final Color backgroundColor;
  final Color foregroundColor;
  final bool useDashboardStyle;

  static String normalizeItem(String value) {
    return value.trim().toLowerCase().replaceAll(RegExp(r'[\s-]+'), '_');
  }

  WalletHeaderNavLeadingMode _resolveLeading() {
    final normalized = leftItems.map(normalizeItem).toList();
    if (normalized.contains('profile')) return WalletHeaderNavLeadingMode.profile;
    if (normalized.contains('back_button') || normalized.contains('back')) {
      return WalletHeaderNavLeadingMode.back;
    }
    return WalletHeaderNavLeadingMode.none;
  }

  List<WalletHeaderNavAction> _resolveActions() {
    final out = <WalletHeaderNavAction>[];
    for (final raw in rightItems) {
      final key = normalizeItem(raw);
      switch (key) {
        case 'statistics':
          out.add(
            WalletHeaderNavAction(
              icon: Icons.bar_chart_rounded,
              onPressed: onStatisticsTap,
              foregroundColor: foregroundColor,
            ),
          );
          break;
        case 'notifications':
          out.add(
            WalletHeaderNavAction(
              icon: Icons.notifications_outlined,
              onPressed: onNotificationTap,
              showDot: showNotificationDot,
              foregroundColor: foregroundColor,
            ),
          );
          break;
        case 'favorite':
          out.add(
            WalletHeaderNavAction(
              icon: Icons.favorite_border_rounded,
              onPressed: onFavoriteTap,
              foregroundColor: foregroundColor,
            ),
          );
          break;
        case 'share':
          out.add(
            WalletHeaderNavAction(
              icon: Icons.share_rounded,
              onPressed: onShareTap,
              foregroundColor: foregroundColor,
            ),
          );
          break;
        default:
          break;
      }
    }
    return out;
  }

  @override
  Widget build(BuildContext context) {
    return WalletHeaderNavBar(
      progress: 0,
      leadingMode: _resolveLeading(),
      customRightActions: _resolveActions(),
      onBackTap: onBackTap,
      onAvatarTap: onProfileTap,
      showAvatarDot: showProfileDot,
      showNotificationDot: showNotificationDot,
    );
  }
}
