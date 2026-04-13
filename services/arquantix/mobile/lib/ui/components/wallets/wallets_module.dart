import 'package:flutter/material.dart';

import '../../../design_system/design_system.dart';
import '../transaction/transaction_avatar.dart';
import '../transaction/transaction_tile.dart';
import '../../theme/app_colors.dart' as ui_theme;

class WalletItem {
  const WalletItem({
    required this.title,
    this.subtitle,
    required this.balance,
    this.numericBalance = 0,
    this.change,
    required this.icon,
    required this.iconBackgroundColor,
  });

  final String title;
  final String? subtitle;
  final String balance;
  /// Valeur numerique pour le calcul de la somme totale dans le header.
  final double numericBalance;
  final String? change;
  final IconData icon;
  final Color iconBackgroundColor;

  Color? get changeColor {
    if (change == null || change!.isEmpty) return null;
    if (change!.startsWith('+')) return ui_theme.AppColors.positive;
    if (change!.startsWith('-')) return ui_theme.AppColors.negative;
    return ui_theme.AppColors.neutral;
  }
}

/// Donnees par defaut pour le module Wallets.
/// Les balances sont a 0 tant que les tables backend ne sont pas creees.
/// Seul "Compte Euro" est branche sur le vrai backend.
List<WalletItem> get mockWalletItems => [
      const WalletItem(
        title: 'Euro Account',
        subtitle: 'Consider investing!',
        balance: '0,00 \u20ac',
        icon: Icons.euro_rounded,
        iconBackgroundColor: AppColors.blue,
      ),
      const WalletItem(
        title: 'Projets d\u0027\u00e9pargne',
        subtitle: 'Open your first project!',
        balance: '0,00 \u20ac',
        icon: Icons.savings_rounded,
        iconBackgroundColor: AppColors.green,
      ),
      const WalletItem(
        title: 'Exclusive offers',
        subtitle: 'Lorem ipsum dolor it',
        balance: '0,00 \u20ac',
        icon: Icons.percent_rounded,
        iconBackgroundColor: AppColors.purple,
      ),
      const WalletItem(
        title: 'Managed Portfolio',
        subtitle: 'Lorem ipsum dolor it',
        balance: '0,00 \u20ac',
        icon: Icons.pie_chart_rounded,
        iconBackgroundColor: AppColors.pink,
      ),
      const WalletItem(
        title: 'Crypto',
        subtitle: '0 crypto-actif',
        balance: '0,00 \u20ac',
        icon: Icons.currency_bitcoin_rounded,
        iconBackgroundColor: AppColors.orange,
      ),
    ];

/// Module blanc : liste de comptes en tuiles.
class WalletsModule extends StatelessWidget {
  const WalletsModule({
    super.key,
    this.items,
    this.onWalletTap,
    this.margin,
  });

  final List<WalletItem>? items;
  final void Function(WalletItem item)? onWalletTap;
  final EdgeInsetsGeometry? margin;

  static const EdgeInsets _defaultMargin = EdgeInsets.symmetric(horizontal: 16, vertical: 12);
  static const double _paddingVertical = 8;
  static const double _borderRadius = 24;

  @override
  Widget build(BuildContext context) {
    final list = items ?? mockWalletItems;

    return Container(
      margin: margin ?? _defaultMargin,
      decoration: BoxDecoration(
        color: AppColors.cardBackground,
        borderRadius: BorderRadius.circular(_borderRadius),
        boxShadow: [
          BoxShadow(
            color: AppColors.textPrimary.withValues(alpha: 0.06),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(_borderRadius),
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: _paddingVertical),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: list
                .map(
                  (item) => TransactionTile(
                    avatar: TransactionAvatar(
                      icon: item.icon,
                      backgroundColor: item.iconBackgroundColor,
                      iconColor: Colors.white,
                    ),
                    title: item.title,
                    subtitle: item.subtitle,
                    rightPrimary: item.balance,
                    rightSecondary: item.change,
                    rightSecondaryColor: item.changeColor,
                    onTap: onWalletTap != null ? () => onWalletTap!(item) : null,
                  ),
                )
                .toList(),
          ),
        ),
      ),
    );
  }
}
