import 'package:flutter/material.dart';

import '../../../../../core/config.dart';
import '../../../../../design_system/design_system.dart';
import '../../../data/lifi_swap_api.dart';
import 'lifi_swap_flow_format.dart';
import 'lifi_swap_from_selection_screen.dart';

/// Étape 1 — choix de l'actif destination (whitelist LI.FI).
class LifiSwapToSelectionScreen extends StatefulWidget {
  const LifiSwapToSelectionScreen({super.key});

  @override
  State<LifiSwapToSelectionScreen> createState() =>
      _LifiSwapToSelectionScreenState();
}

class _LifiSwapToSelectionScreenState extends State<LifiSwapToSelectionScreen> {
  final _api = const LifiSwapApi();
  final _searchController = TextEditingController();

  LifiSwapCatalog? _catalog;
  bool _loading = true;
  String? _error;
  String _query = '';
  final Map<String, String> _selectedChains = {};

  @override
  void initState() {
    super.initState();
    _searchController.addListener(() {
      setState(() => _query = _searchController.text.trim().toLowerCase());
    });
    _load();
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final catalog = await _api.fetchCatalog();
      if (!mounted) return;
      setState(() {
        _catalog = catalog;
        _loading = false;
        for (final asset in catalog.destinationAssets) {
          _selectedChains[asset.symbol] = LifiSwapFlowFormat.defaultChainForAsset(
            asset.symbol,
            asset.chains,
          );
        }
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  List<LifiSwapAsset> get _destinationAssets {
    final raw = _catalog?.destinationAssets ?? _catalog?.assets ?? const [];
    return raw.where((a) => LifiSwapFlowFormat.isV1Token(a.symbol)).toList(growable: false);
  }

  List<LifiSwapAsset> get _filteredAssets {
    final assets = _destinationAssets;
    if (_query.isEmpty) return assets;
    return assets
        .where(
          (a) =>
              a.symbol.toLowerCase().contains(_query) ||
              a.displayName.toLowerCase().contains(_query),
        )
        .toList(growable: false);
  }

  void _selectAsset(LifiSwapAsset asset) {
    final chain = _selectedChains[asset.symbol] ??
        LifiSwapFlowFormat.defaultChainForAsset(asset.symbol, asset.chains);
    Navigator.of(context).push<bool>(
      MaterialPageRoute<bool>(
        builder: (_) => LifiSwapFromSelectionScreen(
          toAsset: asset.symbol,
          toAssetName: asset.displayName,
          toChain: chain,
          catalog: _catalog!,
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
          : _error != null
              ? _buildError()
              : _buildBody(),
    );
  }

  Widget _buildError() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(AppSpacing.xl),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              _error ?? 'Erreur',
              textAlign: TextAlign.center,
              style: AppTypography.bodyMedium.copyWith(color: AppColors.textSecondary),
            ),
            const SizedBox(height: AppSpacing.lg),
            AppPrimaryButton(label: 'Réessayer', onPressed: _load),
          ],
        ),
      ),
    );
  }

  Widget _buildBody() {
    final assets = _filteredAssets;
    return ListView(
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
      children: [
        const SizedBox(height: AppSpacing.md),
        AppPageTitle('Swap'),
        const SizedBox(height: 8),
        Text(
          'Vers quelle crypto ?',
          style: AppTypography.titleLarge.copyWith(
            color: AppColors.textPrimary,
            fontWeight: FontWeight.w700,
            height: 1.35,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          'USDC, USDT ou ETH — chaînes EVM uniquement.',
          style: AppTypography.bodyMedium.copyWith(color: AppColors.textSecondary),
        ),
        const SizedBox(height: AppSpacing.xl),
        _SearchBar(controller: _searchController),
        const SizedBox(height: AppSpacing.lg),
        AppSectionTitle2('Cryptos · ${assets.length}'),
        const SizedBox(height: 12),
        ...assets.map(_buildAssetCard),
        const SizedBox(height: AppSpacing.xxl),
      ],
    );
  }

  Widget _buildAssetCard(LifiSwapAsset asset) {
    final chain = _selectedChains[asset.symbol] ??
        LifiSwapFlowFormat.defaultChainForAsset(asset.symbol, asset.chains);
    final slug = asset.symbol.trim().toLowerCase();
    final logoUrl = Config.resolveLogoUrl('/media/crypto_logos/$slug.png');

    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          TransactionListCard(
            itemSpacing: 0,
            items: [
              TransactionListItemData(
                leadingWidget: CryptoAvatar(
                  ticker: asset.symbol,
                  logoUrl: logoUrl,
                  size: CryptoAvatarSize.large,
                ),
                title: asset.displayName,
                subtitle: asset.symbol,
                amount: '',
                onTap: () => _selectAsset(asset),
              ),
            ],
          ),
          if (asset.chains.length > 1)
            Padding(
              padding: const EdgeInsets.only(top: 8, left: 4),
              child: _ChainChips(
                chains: LifiSwapFlowFormat.filterEvmChains(asset.chains),
                selected: chain,
                onSelected: (c) => setState(() => _selectedChains[asset.symbol] = c),
              ),
            ),
        ],
      ),
    );
  }
}

class _SearchBar extends StatelessWidget {
  const _SearchBar({required this.controller});
  final TextEditingController controller;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(999),
        boxShadow: [
          BoxShadow(
            color: AppColors.textPrimary.withValues(alpha: 0.08),
            blurRadius: 14,
            offset: const Offset(0, 3),
          ),
        ],
      ),
      child: TextField(
        controller: controller,
        style: AppTypography.bodyMedium.copyWith(color: AppColors.textPrimary),
        decoration: InputDecoration(
          prefixIcon: const Icon(Icons.search_rounded),
          prefixIconColor: AppColors.textSecondary,
          hintText: 'Rechercher',
          hintStyle: AppTypography.bodyMedium.copyWith(color: AppColors.textSecondary),
          border: InputBorder.none,
          contentPadding: const EdgeInsets.symmetric(vertical: AppSpacing.md),
        ),
      ),
    );
  }
}

class _ChainChips extends StatelessWidget {
  const _ChainChips({
    required this.chains,
    required this.selected,
    required this.onSelected,
  });

  final List<String> chains;
  final String selected;
  final ValueChanged<String> onSelected;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 6,
      runSpacing: 4,
      children: [
        for (final chain in chains)
          GestureDetector(
            onTap: () => onSelected(chain),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(
                color: chain == selected ? AppColors.indigo.withValues(alpha: 0.12) : Colors.white,
                borderRadius: BorderRadius.circular(999),
                border: Border.all(
                  color: chain == selected ? AppColors.indigo : AppColors.border,
                ),
              ),
              child: Text(
                LifiSwapFlowFormat.chainLabel(chain),
                style: AppTypography.meta.copyWith(
                  color: chain == selected ? AppColors.indigo : AppColors.textSecondary,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ),
      ],
    );
  }
}
