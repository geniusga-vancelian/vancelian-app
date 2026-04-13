import 'package:flutter/material.dart';

import '../../../../../design_system/design_system.dart';
import '../../../../markets/data/product_catalog_api.dart';
import 'bundle_invest_flow_controller.dart';
import 'bundle_source_selection_screen.dart';

/// STEP 0 — Bundle selection.
///
/// Displays the list of investable bundles (crypto_bundle products).
class BundleSelectionScreen extends StatefulWidget {
  const BundleSelectionScreen({super.key});

  @override
  State<BundleSelectionScreen> createState() => _BundleSelectionScreenState();
}

class _BundleSelectionScreenState extends State<BundleSelectionScreen> {
  final ProductCatalogApi _catalogApi = ProductCatalogApi();
  bool _loading = true;
  List<ProductCatalogItem> _bundles = [];

  @override
  void initState() {
    super.initState();
    _loadBundles();
  }

  Future<void> _loadBundles() async {
    try {
      List<ProductCatalogItem> items;
      try {
        items = await _catalogApi.getBundleCatalog();
      } catch (_) {
        items = await _catalogApi.getCatalog(productType: 'crypto_bundle');
      }
      if (!mounted) return;
      setState(() {
        _bundles = items;
        _loading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _loading = false);
    }
  }

  void _selectBundle(ProductCatalogItem item) {
    final bundle = BundleItem(
      portfolioId: item.portfolioId ?? '',
      productId: item.id,
      name: item.name,
      description: item.description ?? item.allocationsSummary,
      entryAssetDefault: item.entryAssetDefault ?? 'USDC',
      entryAssetsAllowed: item.entryAssetsAllowed ?? ['USDC'],
      allocations: item.allocations
          .map((a) => BundleAllocationTarget(
                asset: a.assetSymbol,
                weight: a.targetWeight,
              ))
          .toList(),
    );

    Navigator.of(context).push<bool>(
      MaterialPageRoute<bool>(
        builder: (_) => BundleSourceSelectionScreen(bundle: bundle),
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
          : _bundles.isEmpty
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 32),
                    child: Text(
                      'Aucun bundle disponible',
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
    return ListView(
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
      children: [
        const SizedBox(height: AppSpacing.md),
        const AppPageTitle('Investir dans un bundle'),
        const SizedBox(height: 8),
        Text(
          'Dans quel bundle souhaitez-vous investir ?',
          style: AppTypography.titleLarge.copyWith(
            color: AppColors.textPrimary,
            fontWeight: FontWeight.w700,
            height: 1.35,
          ),
        ),
        const SizedBox(height: 32),
        ..._bundles.map(_buildBundleRow),
        const SizedBox(height: 32),
      ],
    );
  }

  Widget _buildBundleRow(ProductCatalogItem item) {
    final allocSummary = item.allocationsSummary;

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Material(
        color: AppColors.cardBackground,
        borderRadius: BorderRadius.circular(20),
        elevation: 0,
        child: InkWell(
          onTap: () => _selectBundle(item),
          borderRadius: BorderRadius.circular(20),
          child: Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(20),
              boxShadow: [
                BoxShadow(
                  color: AppColors.textPrimary.withValues(alpha: 0.06),
                  blurRadius: 8,
                  offset: const Offset(0, 2),
                ),
              ],
            ),
            child: Row(
              children: [
                Container(
                  width: 48,
                  height: 48,
                  decoration: BoxDecoration(
                    color: AppColors.indigo.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  alignment: Alignment.center,
                  child: const Icon(
                    Icons.auto_awesome_mosaic_rounded,
                    size: 24,
                    color: AppColors.indigo,
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        item.name,
                        style: AppTypography.bodyMedium.copyWith(
                          color: AppColors.textPrimary,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        allocSummary.isNotEmpty
                            ? allocSummary
                            : (item.description ?? ''),
                        style: AppTypography.bodySmall.copyWith(
                          color: AppColors.textSecondary,
                        ),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                Icon(
                  Icons.chevron_right_rounded,
                  color: AppColors.textSecondary.withValues(alpha: 0.5),
                  size: 22,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
