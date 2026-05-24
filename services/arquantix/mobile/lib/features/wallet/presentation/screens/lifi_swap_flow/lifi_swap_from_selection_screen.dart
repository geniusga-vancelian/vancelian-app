import 'package:flutter/material.dart';

import '../../../../../core/config.dart';
import '../../../../../design_system/design_system.dart';
import '../../../data/crypto_positions_api.dart';
import '../../../data/lifi_swap_api.dart';
import 'lifi_swap_amount_screen.dart';
import 'lifi_swap_flow_format.dart';
import 'lifi_swap_flow_models.dart';

/// Étape 2 — choix du wallet source.
class LifiSwapFromSelectionScreen extends StatefulWidget {
  const LifiSwapFromSelectionScreen({
    super.key,
    required this.toAsset,
    required this.toAssetName,
    required this.toChain,
    required this.catalog,
  });

  final String toAsset;
  final String toAssetName;
  final String toChain;
  final LifiSwapCatalog catalog;

  @override
  State<LifiSwapFromSelectionScreen> createState() =>
      _LifiSwapFromSelectionScreenState();
}

class _LifiSwapFromSelectionScreenState extends State<LifiSwapFromSelectionScreen> {
  final _cryptoApi = const CryptoPositionsApi();

  bool _loading = true;
  final List<LifiSwapSourceAccount> _accounts = [];

  @override
  void initState() {
    super.initState();
    _loadAccounts();
  }

  Future<void> _loadAccounts() async {
    final sourceAssets = widget.catalog.sourceAssets
        .where((a) => LifiSwapFlowFormat.isV1Token(a.symbol))
        .toList(growable: false);
    final catalogBySymbol = {
      for (final a in sourceAssets) a.symbol.toUpperCase(): a,
    };
    final accounts = <LifiSwapSourceAccount>[];

    try {
      final cryptoData = await _cryptoApi.fetchPositions();
      for (final pos in cryptoData.positions) {
        final sym = pos.asset.toUpperCase();
        final meta = catalogBySymbol[sym];
        if (meta == null) continue;
        final balance = pos.availableBalance > 0 ? pos.availableBalance : pos.balance;
        if (balance <= 0) continue;
        final chain = LifiSwapFlowFormat.defaultChainForAsset(sym, meta.chains);
        if (sym == widget.toAsset.toUpperCase() && chain == widget.toChain) continue;
        accounts.add(
          LifiSwapSourceAccount(
            asset: sym,
            label: pos.name,
            chain: chain,
            balance: balance,
            logoUrl: _resolveLogoUrl(pos.iconKey, pos.asset),
          ),
        );
      }
    } catch (_) {}

    if (accounts.isEmpty) {
      for (final meta in sourceAssets) {
        final chain = LifiSwapFlowFormat.defaultChainForAsset(meta.symbol, meta.chains);
        if (meta.symbol == widget.toAsset && chain == widget.toChain) continue;
        accounts.add(
          LifiSwapSourceAccount(
            asset: meta.symbol,
            label: meta.displayName,
            chain: chain,
            balance: 0,
            logoUrl: Config.resolveLogoUrl(
              '/media/crypto_logos/${meta.symbol.toLowerCase()}.png',
            ),
          ),
        );
      }
    }

    if (!mounted) return;
    setState(() {
      _accounts
        ..clear()
        ..addAll(accounts);
      _loading = false;
    });
  }

  void _selectSource(LifiSwapSourceAccount source) {
    Navigator.of(context).push<bool>(
      MaterialPageRoute<bool>(
        builder: (_) => LifiSwapAmountScreen(
          fromAsset: source.asset,
          fromAssetName: source.label,
          fromChain: source.chain,
          fromLogoUrl: source.logoUrl,
          toAsset: widget.toAsset,
          toAssetName: widget.toAssetName,
          toChain: widget.toChain,
          sourceBalance: source.balance,
        ),
      ),
    ).then((didSwap) {
      if (didSwap == true && mounted) {
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
          ? const Center(child: CircularProgressIndicator(color: AppColors.indigo))
          : _accounts.isEmpty
              ? _buildEmpty()
              : _buildBody(),
    );
  }

  Widget _buildEmpty() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 32),
        child: Text(
          'Aucun wallet éligible avec solde. Effectuez un dépôt crypto d\'abord.',
          style: AppTypography.bodyLarge.copyWith(color: AppColors.textSecondary),
          textAlign: TextAlign.center,
        ),
      ),
    );
  }

  Widget _buildBody() {
    return ListView(
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
      children: [
        const SizedBox(height: AppSpacing.md),
        AppPageTitle('Swap'),
        const SizedBox(height: 8),
        Text(
          'Depuis quel wallet ?',
          style: AppTypography.titleLarge.copyWith(
            color: AppColors.textPrimary,
            fontWeight: FontWeight.w700,
            height: 1.35,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          'Wallets EVM — USDC, USDT ou ETH avec solde.',
          style: AppTypography.bodyMedium.copyWith(color: AppColors.textSecondary),
        ),
        const SizedBox(height: 32),
        AppSectionTitle2('Wallets crypto'),
        const SizedBox(height: 12),
        TransactionListCard(
          itemSpacing: 4,
          items: _accounts.map((account) {
            return TransactionListItemData(
              leadingWidget: CryptoAvatar(
                ticker: account.asset,
                logoUrl: account.logoUrl,
                size: CryptoAvatarSize.large,
              ),
              title: account.label,
              subtitle:
                  '${LifiSwapFlowFormat.chainLabel(account.chain)} · Swap',
              amount:
                  '${LifiSwapFlowFormat.formatCryptoAmount(account.balance)} ${account.asset}',
              onTap: () => _selectSource(account),
            );
          }).toList(),
        ),
        const SizedBox(height: AppSpacing.xxl),
      ],
    );
  }

  static String? _resolveLogoUrl(String iconKey, String asset) {
    final key = iconKey.trim().isNotEmpty
        ? iconKey.trim().toLowerCase()
        : asset.trim().toLowerCase();
    if (key.isEmpty) return null;
    return Config.resolveLogoUrl('/media/crypto_logos/$key.png');
  }
}
