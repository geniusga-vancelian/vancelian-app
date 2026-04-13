import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../../../core/config.dart';
import '../../../../../design_system/design_system.dart';
import '../../../data/cash_api.dart';
import '../../../data/crypto_positions_api.dart';
import 'buy_flow_controller.dart';
import 'buy_flow_amount_screen.dart';
import '../swap_flow/swap_flow_amount_screen.dart';

/// STEP 1 — Source account selection.
///
/// Classic page layout with [AppTopNavBar] (back button only),
/// an [AppPageTitle], and account rows using DS [TransactionListCard].
class BuyFlowSourceSelectionScreen extends StatefulWidget {
  const BuyFlowSourceSelectionScreen({
    super.key,
    required this.assetSymbol,
    required this.assetName,
    this.assetLogoUrl,
  });

  final String assetSymbol;
  final String assetName;
  final String? assetLogoUrl;

  @override
  State<BuyFlowSourceSelectionScreen> createState() =>
      _BuyFlowSourceSelectionScreenState();
}

class _BuyFlowSourceSelectionScreenState
    extends State<BuyFlowSourceSelectionScreen> {
  final CashApi _cashApi = const CashApi();
  final CryptoPositionsApi _cryptoApi = const CryptoPositionsApi();

  bool _loading = true;
  final List<BuyFlowSourceAccount> _accounts = [];

  static final _eurFormatter = NumberFormat.currency(
    locale: 'fr_FR',
    symbol: '€',
    decimalDigits: 2,
  );

  @override
  void initState() {
    super.initState();
    _loadAccounts();
  }

  Future<void> _loadAccounts() async {
    final List<BuyFlowSourceAccount> accounts = [];

    try {
      final cashData = await _cashApi.fetchCashData();
      final account = cashData.cashAccount;
      if (account != null) {
        accounts.add(BuyFlowSourceAccount(
          type: 'fiat',
          label: 'Compte Euro',
          balance: account.availableBalance,
          currency: account.currency,
          currencySymbol: account.currencySymbol,
          icon: Icons.euro_rounded,
          iconBackgroundColor: Colors.blue,
        ));
      }
    } catch (_) {}

    try {
      final cryptoData = await _cryptoApi.fetchPositions();
      for (final pos in cryptoData.positions) {
        if (pos.asset.toUpperCase() == widget.assetSymbol.toUpperCase()) continue;
        if (pos.balance <= 0) continue;
        accounts.add(BuyFlowSourceAccount(
          type: 'crypto',
          label: pos.name,
          balance: pos.balance,
          currency: pos.asset,
          currencySymbol: pos.asset,
          icon: Icons.currency_bitcoin_rounded,
          iconBackgroundColor:
              AppColors.cryptoAssetBrand[pos.asset.toUpperCase()] ??
                  AppColors.textSecondary,
          asset: pos.asset,
          logoUrl: _resolveLogoUrl(pos.iconKey, pos.asset),
        ));
      }
    } catch (_) {}

    if (!mounted) return;
    setState(() {
      _accounts
        ..clear()
        ..addAll(accounts);
      _loading = false;
    });
  }

  void _selectSource(BuyFlowSourceAccount source) {
    if (source.isCrypto) {
      Navigator.of(context).push<bool>(
        MaterialPageRoute<bool>(
          builder: (_) => SwapFlowAmountScreen(
            fromAsset: source.asset ?? source.currency,
            fromAssetName: source.label,
            toAsset: widget.assetSymbol,
            toAssetName: widget.assetName,
            toAssetLogoUrl: widget.assetLogoUrl,
            sourceAccount: source,
          ),
        ),
      ).then((didSwap) {
        if (didSwap == true && mounted) {
          Navigator.of(context).pop(true);
        }
      });
    } else {
      Navigator.of(context).push<bool>(
        MaterialPageRoute<bool>(
          builder: (_) => BuyFlowAmountScreen(
            assetSymbol: widget.assetSymbol,
            assetName: widget.assetName,
            assetLogoUrl: widget.assetLogoUrl,
            sourceAccount: source,
          ),
        ),
      ).then((didBuy) {
        if (didBuy == true && mounted) {
          Navigator.of(context).pop(true);
        }
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      appBar: AppTopNavBar(
        leadingType: AppTopNavBarLeading.back,
        onBackTap: () => Navigator.of(context).pop(false),
        actions: const [],
      ),
      body: _loading
          ? const Center(
              child: CircularProgressIndicator(
                color: AppColors.indigo,
                strokeWidth: 2,
              ),
            )
          : _accounts.isEmpty
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 32),
                    child: Text(
                      'Aucun compte disponible',
                      style: AppTypography.bodyLarge.copyWith(
                        color: AppColors.textSecondary,
                      ),
                      textAlign: TextAlign.center,
                    ),
                  ),
                )
              : _buildBody(),
    );
  }

  Widget _buildBody() {
    final fiatAccounts = _accounts.where((a) => a.isFiat).toList();
    final cryptoAccounts = _accounts.where((a) => a.isCrypto).toList();

    return ListView(
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
      children: [
        const SizedBox(height: AppSpacing.md),
        AppPageTitle('Acheter du ${widget.assetName}'),
        const SizedBox(height: 8),
        Text(
          'À partir de quel compte souhaitez-vous investir ?',
          style: AppTypography.titleLarge.copyWith(
            color: AppColors.textPrimary,
            fontWeight: FontWeight.w700,
            height: 1.35,
          ),
        ),
        const SizedBox(height: 32),
        if (fiatAccounts.isNotEmpty) ...[
          AppSectionTitle2('Comptes fiat'),
          const SizedBox(height: 12),
          _buildAccountsCard(fiatAccounts),
        ],
        if (cryptoAccounts.isNotEmpty) ...[
          const SizedBox(height: 28),
          AppSectionTitle2('Wallets crypto'),
          const SizedBox(height: 12),
          _buildAccountsCard(cryptoAccounts),
        ],
        const SizedBox(height: 32),
      ],
    );
  }

  Widget _buildAccountsCard(List<BuyFlowSourceAccount> accounts) {
    return TransactionListCard(
      itemSpacing: 4,
      items: accounts.map((account) {
        final balanceText = account.isFiat
            ? _eurFormatter.format(account.balance)
            : '${_formatCryptoBalance(account.balance)} ${account.currency}';

        final ticker = account.isFiat
            ? 'EUR'
            : (account.asset ?? account.currency).toUpperCase();

        return TransactionListItemData(
          leadingWidget: CryptoAvatar(
            ticker: ticker,
            logoUrl: account.logoUrl,
            fallbackIcon: account.isFiat
                ? Icons.euro_rounded
                : Icons.token_outlined,
            size: CryptoAvatarSize.large,
          ),
          title: account.label,
          subtitle: account.isCrypto ? 'Swap' : '',
          amount: balanceText,
          onTap: () => _selectSource(account),
        );
      }).toList(),
    );
  }

  static String? _resolveLogoUrl(String iconKey, String asset) {
    final key = iconKey.trim().isNotEmpty
        ? iconKey.trim().toLowerCase()
        : asset.trim().toLowerCase();
    if (key.isEmpty) return null;
    return Config.resolveLogoUrl('/media/crypto_logos/$key.png');
  }

  String _formatCryptoBalance(double amount) {
    if (amount < 0.0001) return amount.toStringAsExponential(2);
    if (amount < 1) return amount.toStringAsFixed(6);
    return amount.toStringAsFixed(4);
  }
}
