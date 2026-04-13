import 'package:flutter/material.dart';

import '../../core/config.dart';
import '../../features/wallet/domain/models/cash_data.dart';
import '../../features/wallet/domain/models/transaction_ui_model.dart';
import '../../features/wallet/presentation/screens/transaction_list_screen.dart';
import '../../features/wallet/presentation/screens/transaction_screen.dart';
import '../atoms/atoms.dart';
import 'transaction_list_card.dart';
import 'transaction_swap_avatar.dart';

enum _DataState { loading, loaded, empty, error }

class TransactionLatest10Module extends StatelessWidget {
  const TransactionLatest10Module({
    super.key,
    this.title = 'Latest transactions',
    this.walletId = 0,
    this.limit = 10,
    this.transactions,
    this.currencySymbol = '€',
    this.isLoading = false,
    this.hasError = false,
  });

  final String title;
  final int walletId;
  final int limit;

  /// Real backend transactions. When provided, mocks are ignored.
  final List<CashTransaction>? transactions;

  final String currencySymbol;
  final bool isLoading;
  final bool hasError;

  _DataState get _state {
    if (isLoading) return _DataState.loading;
    if (hasError) return _DataState.error;
    if (transactions != null && transactions!.isEmpty) return _DataState.empty;
    return _DataState.loaded;
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (title.trim().isNotEmpty) _buildHeader(context),
        _buildBody(context),
      ],
    );
  }

  Widget _buildHeader(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(AppRadius.sm),
          onTap: transactions != null && transactions!.isNotEmpty
              ? () => _openFullList(context)
              : null,
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Align(
              alignment: Alignment.centerLeft,
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(title, style: AppTypography.headerPrimary),
                  const SizedBox(width: 2),
                  const Icon(
                    Icons.chevron_right_rounded,
                    size: 26,
                    color: AppColors.textPrimary,
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildBody(BuildContext context) {
    switch (_state) {
      case _DataState.loading:
        return _buildLoadingState();
      case _DataState.error:
        return _buildErrorState();
      case _DataState.empty:
        return _buildEmptyState();
      case _DataState.loaded:
        if (transactions != null) {
          return _buildRealTransactions(context);
        }
        return _buildMockTransactions(context);
    }
  }

  Widget _buildLoadingState() {
    return _ModuleContainer(
      child: Column(
        children: List.generate(3, (_) => _buildSkeletonTile()),
      ),
    );
  }

  Widget _buildSkeletonTile() {
    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpacing.lg,
        vertical: AppSpacing.md,
      ),
      child: Row(
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(10),
              color: Colors.grey.shade200,
            ),
          ),
          const SizedBox(width: AppSpacing.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  height: 14,
                  width: 120,
                  decoration: BoxDecoration(
                    color: Colors.grey.shade200,
                    borderRadius: BorderRadius.circular(4),
                  ),
                ),
                const SizedBox(height: AppSpacing.sm),
                Container(
                  height: 12,
                  width: 80,
                  decoration: BoxDecoration(
                    color: Colors.grey.shade100,
                    borderRadius: BorderRadius.circular(4),
                  ),
                ),
              ],
            ),
          ),
          Container(
            height: 14,
            width: 70,
            decoration: BoxDecoration(
              color: Colors.grey.shade200,
              borderRadius: BorderRadius.circular(4),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyState() {
    return _ModuleContainer(
      child: Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.lg,
          vertical: AppSpacing.xxl,
        ),
        child: Center(
          child: Column(
            children: [
              Icon(Icons.receipt_long_rounded, size: 36, color: Colors.grey.shade400),
              const SizedBox(height: AppSpacing.sm),
              Text(
                'Aucune transaction pour le moment',
                style: AppTypography.bodyMedium.copyWith(color: AppColors.textMuted),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildErrorState() {
    return _ModuleContainer(
      child: Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpacing.lg,
          vertical: AppSpacing.xxl,
        ),
        child: Center(
          child: Column(
            children: [
              Icon(Icons.error_outline_rounded, size: 36, color: Colors.grey.shade400),
              const SizedBox(height: AppSpacing.sm),
              Text(
                'Impossible de charger les transactions',
                style: AppTypography.bodyMedium.copyWith(color: AppColors.textMuted),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildRealTransactions(BuildContext context) {
    final normalizedLimit = limit <= 0 ? 10 : limit;
    final uiModels = TransactionUiModel.fromCashTransactions(
      transactions!.take(normalizedLimit).toList(),
      currencySymbol: currencySymbol,
    );

    return TransactionListCard(
      itemSpacing: AppSpacing.lg,
      items: uiModels.map((tx) {
        return _buildItemData(context, tx);
      }).toList(),
    );
  }

  static TransactionListItemData _buildItemData(BuildContext context, TransactionUiModel tx) {
    if (tx.isExchange && tx.cryptoTicker != null) {
      final ticker = tx.cryptoTicker!;
      final logoUrl = Config.resolveLogoUrl(
        '/media/crypto_logos/${ticker.toLowerCase()}.png',
      );
      return TransactionListItemData(
        leadingWidget: TransactionSwapAvatar(
          fromTicker: tx.isExchangeBuy ? 'EUR' : ticker,
          toTicker: tx.isExchangeBuy ? ticker : 'EUR',
          fromLogoUrl: tx.isExchangeBuy ? null : logoUrl,
          toLogoUrl: tx.isExchangeBuy ? logoUrl : null,
          fromIcon: tx.isExchangeBuy ? Icons.euro_rounded : null,
          toIcon: tx.isExchangeBuy ? null : Icons.euro_rounded,
        ),
        title: tx.title,
        subtitle: tx.subtitle,
        amount: tx.formattedAmount,
        secondaryAmount: tx.dateLabel,
        onTap: () {
          Navigator.of(context).push(
            MaterialPageRoute<void>(
              builder: (_) => TransactionScreen(
                transactionId: tx.id,
                merchant: tx.title,
                dateTime: tx.dateLabel,
                amount: tx.formattedAmount,
                icon: tx.icon,
                iconColor: tx.iconBackground,
              ),
            ),
          );
        },
      );
    }

    return TransactionListItemData(
      icon: tx.icon,
      iconColor: Colors.white,
      avatarBackgroundColor: tx.iconBackground,
      title: tx.title,
      subtitle: tx.subtitle,
      amount: tx.formattedAmount,
      amountColor: tx.amountColor,
      secondaryAmount: tx.dateLabel,
      onTap: () {
        Navigator.of(context).push(
          MaterialPageRoute<void>(
            builder: (_) => TransactionScreen(
              transactionId: tx.id,
              merchant: tx.title,
              dateTime: tx.dateLabel,
              amount: tx.formattedAmount,
              icon: tx.icon,
              iconColor: tx.iconBackground,
            ),
          ),
        );
      },
    );
  }

  void _openFullList(BuildContext context) {
    if (transactions == null) return;
    final uiModels = TransactionUiModel.fromCashTransactions(
      transactions!,
      currencySymbol: currencySymbol,
    );
    final items = uiModels
        .map(
          (tx) => TransactionListItem(
            transactionId: tx.id,
            merchant: tx.title,
            dateTime: tx.fullDateTime,
            amount: tx.formattedAmount,
            icon: tx.icon,
            iconColor: tx.iconBackground,
            cryptoTicker: tx.cryptoTicker,
            isExchangeBuy: tx.isExchangeBuy,
            exchangeDetail: tx.exchangeDetail,
          ),
        )
        .toList();
    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (_) => TransactionListScreen(transactions: items),
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Legacy mock fallback
  // ---------------------------------------------------------------------------

  Widget _buildMockTransactions(BuildContext context) {
    final normalizedLimit = limit <= 0 ? 10 : limit;
    final filtered = walletId == 0
        ? _mockTransactions
        : _mockTransactions.where((tx) => tx.walletId == walletId).toList();
    final latest = filtered.take(normalizedLimit).toList();

    return TransactionListCard(
      itemSpacing: AppSpacing.lg,
      items: latest.map((tx) {
        final mockDateTime = _mockDateTimeForTransaction(tx.id);
        return TransactionListItemData(
          icon: tx.icon,
          iconColor: Colors.white,
          avatarBackgroundColor: tx.iconBg,
          title: tx.title,
          subtitle: tx.subtitle,
          amount: tx.amount,
          secondaryAmount: tx.delta,
          secondaryAmountColor:
              tx.positive ? AppColors.green : AppColors.textSecondary,
          onTap: () {
            Navigator.of(context).push(
              MaterialPageRoute<void>(
                builder: (_) => TransactionScreen(
                  transactionId: tx.id,
                  merchant: tx.title,
                  dateTime: mockDateTime,
                  amount: tx.amount,
                  icon: tx.icon,
                  iconColor: tx.iconBg,
                ),
              ),
            );
          },
        );
      }).toList(),
    );
  }

  static String _mockDateTimeForTransaction(String transactionId) {
    final raw = transactionId.replaceAll(RegExp(r'[^0-9]'), '');
    final index = int.tryParse(raw) ?? 1;
    final day = (index % 28) + 1;
    final hour = 9 + (index % 10);
    final minute = (index * 7) % 60;
    return '$day mars 2026 • ${hour.toString().padLeft(2, '0')}:${minute.toString().padLeft(2, '0')}';
  }

  static const List<_MockTransaction> _mockTransactions = [
    _MockTransaction(id: 'tx-001', walletId: 1, title: 'Virement entrant', subtitle: 'Compte Euro', amount: '+2 500,00 EUR', delta: "Aujourd'hui", icon: Icons.account_balance_rounded, iconBg: Color(0xFF3B82F6), positive: true),
    _MockTransaction(id: 'tx-002', walletId: 2, title: 'Achat BTC', subtitle: 'Crypto Wallet', amount: '-850,00 EUR', delta: 'Hier', icon: Icons.currency_bitcoin_rounded, iconBg: Color(0xFFF59E0B), positive: false),
    _MockTransaction(id: 'tx-003', walletId: 3, title: 'Dividendes ETF', subtitle: 'Placements', amount: '+74,21 EUR', delta: 'Il y a 2 jours', icon: Icons.trending_up_rounded, iconBg: Color(0xFF22C55E), positive: true),
    _MockTransaction(id: 'tx-004', walletId: 1, title: 'Paiement carte', subtitle: 'Compte Euro', amount: '-43,90 EUR', delta: 'Il y a 2 jours', icon: Icons.credit_card_rounded, iconBg: Color(0xFF6366F1), positive: false),
    _MockTransaction(id: 'tx-005', walletId: 4, title: 'Swap ETH -> BTC', subtitle: 'Paniers Crypto', amount: '+0,0021 BTC', delta: 'Il y a 3 jours', icon: Icons.swap_horiz_rounded, iconBg: Color(0xFF8B5CF6), positive: true),
    _MockTransaction(id: 'tx-006', walletId: 2, title: 'Frais réseau', subtitle: 'Crypto Wallet', amount: '-3,20 EUR', delta: 'Il y a 3 jours', icon: Icons.receipt_long_rounded, iconBg: Color(0xFF64748B), positive: false),
    _MockTransaction(id: 'tx-007', walletId: 3, title: 'Rendement mensuel', subtitle: 'Placements', amount: '+128,45 EUR', delta: 'Il y a 4 jours', icon: Icons.savings_rounded, iconBg: Color(0xFF10B981), positive: true),
    _MockTransaction(id: 'tx-008', walletId: 1, title: 'Retrait SEPA', subtitle: 'Compte Euro', amount: '-500,00 EUR', delta: 'Il y a 5 jours', icon: Icons.outbox_rounded, iconBg: Color(0xFF0EA5E9), positive: false),
    _MockTransaction(id: 'tx-009', walletId: 4, title: 'Rebalancing panier', subtitle: 'Paniers Crypto', amount: '+39,12 EUR', delta: 'Il y a 6 jours', icon: Icons.pie_chart_rounded, iconBg: Color(0xFFA855F7), positive: true),
    _MockTransaction(id: 'tx-010', walletId: 2, title: 'Vente partielle ETH', subtitle: 'Crypto Wallet', amount: '+215,00 EUR', delta: 'Il y a 7 jours', icon: Icons.sell_rounded, iconBg: Color(0xFFF97316), positive: true),
    _MockTransaction(id: 'tx-011', walletId: 3, title: 'Frais de gestion', subtitle: 'Placements', amount: '-12,00 EUR', delta: 'Il y a 8 jours', icon: Icons.settings_rounded, iconBg: Color(0xFF14B8A6), positive: false),
    _MockTransaction(id: 'tx-012', walletId: 1, title: 'Cashback', subtitle: 'Compte Euro', amount: '+6,45 EUR', delta: 'Il y a 9 jours', icon: Icons.redeem_rounded, iconBg: Color(0xFF2563EB), positive: true),
  ];
}

class _MockTransaction {
  const _MockTransaction({
    required this.id,
    required this.walletId,
    required this.title,
    required this.subtitle,
    required this.amount,
    required this.delta,
    required this.icon,
    required this.iconBg,
    required this.positive,
  });

  final String id;
  final int walletId;
  final String title;
  final String subtitle;
  final String amount;
  final String delta;
  final IconData icon;
  final Color iconBg;
  final bool positive;
}

class _ModuleContainer extends StatelessWidget {
  const _ModuleContainer({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.cardBackground,
        borderRadius: BorderRadius.circular(AppRadius.lg),
        boxShadow: AppShadow.defaultShadowList,
      ),
      child: child,
    );
  }
}
