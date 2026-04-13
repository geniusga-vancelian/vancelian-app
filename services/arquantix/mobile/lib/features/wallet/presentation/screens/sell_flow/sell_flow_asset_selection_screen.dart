import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../../../../../core/config.dart';
import '../../../../../core/currency_preference.dart';
import '../../../../../design_system/design_system.dart';
import '../../../../../ui/components/transaction/transaction_avatar.dart';
import '../../../../../ui/components/transaction/transaction_tile.dart';
import '../../../data/crypto_positions_api.dart';
import '../../../domain/models/crypto_positions_data.dart';
import 'sell_flow_destination_selection_screen.dart';

/// STEP 0 — Asset to sell selection.
///
/// Displayed when the user enters the SELL flow without a pre-selected asset.
/// Shows only crypto wallets with balance > 0.
class SellFlowAssetSelectionScreen extends StatefulWidget {
  const SellFlowAssetSelectionScreen({super.key});

  @override
  State<SellFlowAssetSelectionScreen> createState() =>
      _SellFlowAssetSelectionScreenState();
}

class _SellFlowAssetSelectionScreenState
    extends State<SellFlowAssetSelectionScreen> {
  final CryptoPositionsApi _positionsApi = const CryptoPositionsApi();

  bool _loading = true;
  List<CryptoPositionItem> _positions = [];

  static final _fiatFormatterEur = NumberFormat.currency(
    locale: 'fr_FR', symbol: '€', decimalDigits: 2,
  );
  static final _fiatFormatterUsd = NumberFormat.currency(
    locale: 'en_US', symbol: '\$', decimalDigits: 2,
  );

  NumberFormat get _fiatFormatter =>
      CurrencyPreference.instance.currency == ReferenceCurrency.usd
          ? _fiatFormatterUsd
          : _fiatFormatterEur;

  @override
  void initState() {
    super.initState();
    _loadPositions();
  }

  Future<void> _loadPositions() async {
    try {
      final data = await _positionsApi.fetchPositions();
      if (!mounted) return;

      final withBalance = data.positions
          .where((p) => p.balance > 0 || p.availableBalance > 0)
          .toList();

      setState(() {
        _positions = withBalance;
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() {
        _positions = [];
        _loading = false;
      });
    }
  }

  void _selectAsset(CryptoPositionItem pos) {
    Navigator.of(context).push<bool>(
      MaterialPageRoute<bool>(
        builder: (_) => SellFlowDestinationSelectionScreen(
          assetSymbol: pos.asset,
          assetName: pos.name,
          assetLogoUrl: _resolveLogoUrl(pos),
          cryptoBalance: pos.availableBalance > 0 ? pos.availableBalance : pos.balance,
        ),
      ),
    ).then((didSell) {
      if (didSell == true && mounted) {
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
          : _positions.isEmpty
              ? _buildEmptyState()
              : _buildBody(),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.account_balance_wallet_outlined,
              size: 48,
              color: AppColors.textSecondary.withValues(alpha: 0.5),
            ),
            const SizedBox(height: AppSpacing.md),
            Text(
              'Aucun actif à vendre',
              style: AppTypography.titleMedium.copyWith(
                color: AppColors.textPrimary,
                fontWeight: FontWeight.w600,
              ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Text(
              'Vous devez détenir des cryptomonnaies pour pouvoir les vendre.',
              style: AppTypography.meta.copyWith(color: AppColors.textSecondary),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildBody() {
    return ListView(
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
      children: [
        const SizedBox(height: AppSpacing.md),
        AppPageTitle('Vendre'),
        const SizedBox(height: 8),
        Text(
          'Que souhaitez-vous vendre ?',
          style: AppTypography.titleLarge.copyWith(
            color: AppColors.textPrimary,
            fontWeight: FontWeight.w700,
            height: 1.35,
          ),
        ),
        const SizedBox(height: 28),
        _buildPositionsCard(),
        const SizedBox(height: 32),
      ],
    );
  }

  Widget _buildPositionsCard() {
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
          children: _positions.map((pos) {
            final balance = pos.availableBalance > 0 ? pos.availableBalance : pos.balance;
            final value = CurrencyPreference.instance.currency == ReferenceCurrency.usd
                ? (pos.estimatedValueUsd ?? pos.estimatedValueEur ?? 0)
                : (pos.estimatedValueEur ?? pos.estimatedValueUsd ?? 0);
            final valueText = value > 0 ? _fiatFormatter.format(value) : null;

            final brandColor = AppColors.cryptoAssetBrand[pos.asset] ??
                AppColors.textSecondary;
            final logoUrl = _resolveLogoUrl(pos);

            return TransactionTile(
              avatar: TransactionAvatar(
                icon: Icons.currency_bitcoin_rounded,
                backgroundColor: brandColor,
                iconColor: Colors.white,
                imageUrl: logoUrl,
              ),
              title: pos.name,
              subtitle: _formatBalance(pos.asset, balance),
              rightPrimary: valueText,
              onTap: () => _selectAsset(pos),
            );
          }).toList(),
        ),
      ),
    );
  }

  String? _resolveLogoUrl(CryptoPositionItem pos) {
    final logoKey = pos.iconKey.trim().isNotEmpty
        ? pos.iconKey.trim().toLowerCase()
        : pos.asset.trim().toLowerCase();
    if (logoKey.isEmpty) return null;
    return Config.resolveLogoUrl('/media/crypto_logos/$logoKey.png');
  }

  String _formatBalance(String asset, double balance) {
    if (balance >= 1) return '${balance.toStringAsFixed(4)} $asset';
    if (balance >= 0.0001) return balance.toStringAsFixed(8);
    return balance.toString();
  }
}
