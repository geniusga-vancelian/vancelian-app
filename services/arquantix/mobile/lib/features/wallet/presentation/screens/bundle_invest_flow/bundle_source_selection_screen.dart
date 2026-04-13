import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../../../core/config.dart';
import '../../../../../design_system/design_system.dart';
import '../../../../../ui/components/transaction/transaction_avatar.dart';
import '../../../../../ui/components/transaction/transaction_tile.dart';
import '../../../data/cash_api.dart';
import '../../../data/crypto_positions_api.dart';
import 'bundle_invest_flow_controller.dart';
import 'bundle_amount_entry_screen.dart';

/// STEP 1 — Source account selection for bundle investment.
class BundleSourceSelectionScreen extends StatefulWidget {
  const BundleSourceSelectionScreen({
    super.key,
    required this.bundle,
  });

  final BundleItem bundle;

  @override
  State<BundleSourceSelectionScreen> createState() =>
      _BundleSourceSelectionScreenState();
}

class _BundleSourceSelectionScreenState
    extends State<BundleSourceSelectionScreen> {
  final CashApi _cashApi = const CashApi();
  final CryptoPositionsApi _cryptoApi = const CryptoPositionsApi();

  bool _loading = true;
  final List<BundleSourceAccount> _accounts = [];

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
    final List<BundleSourceAccount> accounts = [];

    try {
      final cashData = await _cashApi.fetchCashData();
      final account = cashData.cashAccount;
      if (account != null) {
        accounts.add(BundleSourceAccount(
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

    final allowedUpper =
        widget.bundle.entryAssetsAllowed.map((a) => a.toUpperCase()).toSet();

    try {
      final cryptoData = await _cryptoApi.fetchPositions();
      for (final pos in cryptoData.positions) {
        final assetUpper = pos.asset.toUpperCase();
        if (!allowedUpper.contains(assetUpper)) continue;
        if (pos.balance <= 0) continue;
        accounts.add(BundleSourceAccount(
          type: 'crypto',
          label: 'Wallet ${pos.asset}',
          balance: pos.balance,
          currency: pos.asset,
          currencySymbol: pos.asset,
          icon: Icons.account_balance_wallet_rounded,
          iconBackgroundColor:
              AppColors.cryptoAssetBrand[assetUpper] ?? AppColors.textSecondary,
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

  void _selectSource(BundleSourceAccount source) {
    Navigator.of(context).push<bool>(
      MaterialPageRoute<bool>(
        builder: (_) => BundleAmountEntryScreen(
          bundle: widget.bundle,
          sourceAccount: source,
        ),
      ),
    ).then((result) {
      if (result == true && mounted) {
        Navigator.of(context).pop(true);
      }
    });
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
        AppPageTitle('Investir dans ${widget.bundle.name}'),
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
          const AppSectionTitle2('Comptes fiat'),
          const SizedBox(height: 12),
          _buildAccountsCard(fiatAccounts),
        ],
        if (cryptoAccounts.isNotEmpty) ...[
          const SizedBox(height: 28),
          const AppSectionTitle2('Wallets entry asset'),
          const SizedBox(height: 12),
          _buildAccountsCard(cryptoAccounts),
        ],
        const SizedBox(height: 32),
      ],
    );
  }

  Widget _buildAccountsCard(List<BundleSourceAccount> accounts) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.cardBackground,
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(
            color: AppColors.textPrimary.withValues(alpha: 0.06),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      clipBehavior: Clip.antiAlias,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: accounts.map((account) {
            final balanceText = account.isFiat
                ? _eurFormatter.format(account.balance)
                : '${_formatCryptoBalance(account.balance)} ${account.currency}';

            return TransactionTile(
              avatar: TransactionAvatar(
                icon: account.icon,
                backgroundColor: account.iconBackgroundColor,
                iconColor: Colors.white,
                imageUrl: account.logoUrl,
              ),
              title: account.label,
              subtitle: account.isCrypto ? widget.bundle.entryAssetDefault : null,
              rightPrimary: balanceText,
              onTap: () => _selectSource(account),
            );
          }).toList(),
        ),
      ),
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
