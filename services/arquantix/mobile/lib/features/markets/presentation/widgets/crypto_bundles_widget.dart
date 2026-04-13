import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../../design_system/design_system.dart';
import '../../data/product_catalog_api.dart';
import '../../presentation/screens/product_preview_screen.dart';
import '../../../offers/data/vaults_api.dart';
import '../../../offers/presentation/screens/vault_preview_screen.dart';
import '../../../wallet/presentation/screens/bundle_invest_flow/bundle_invest_flow_controller.dart';

/// Widget dédié "Crypto Bundles" : charge en priorité le feed Portfolio Engine
/// (GET /api/portfolio-engine/products/catalog), sinon fallback sur le widget
/// crypto-bundles. Affiche les bundles avec [AssetsBundlesModule].
class CryptoBundlesWidget extends StatefulWidget {
  const CryptoBundlesWidget({
    super.key,
    this.refreshNonce = 0,
    this.title = 'Crypto Bundles',
  });

  final int refreshNonce;
  final String title;

  @override
  State<CryptoBundlesWidget> createState() => _CryptoBundlesWidgetState();
}

class _CryptoBundlesWidgetState extends State<CryptoBundlesWidget> {
  static const String _widgetSlug = 'crypto-bundles-widget';

  final ProductCatalogApi _catalogApi = ProductCatalogApi();
  final VaultsApi _vaultsApi = VaultsApi();
  bool _loading = true;
  String? _error;
  List<AssetsBundleItem> _items = const [];
  bool _showImageOverlay = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void didUpdateWidget(covariant CryptoBundlesWidget oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.refreshNonce != widget.refreshNonce) {
      _load();
    }
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
      _items = const [];
    });
    try {
      // 1) Priorité : feed enrichi bundle (avec portfolio IDs du client)
      List<ProductCatalogItem> catalogItems;
      try {
        catalogItems = await _catalogApi.getBundleCatalog();
      } catch (_) {
        catalogItems = await _catalogApi.getCatalog(productType: 'crypto_bundle');
      }
      if (!mounted) return;
      if (catalogItems.isNotEmpty) {
        final displayConfigs = await _catalogApi.getDisplayConfigs();
        if (!mounted) return;

        final published = catalogItems
            .where((p) => displayConfigs.containsKey(p.productCode))
            .toList();

        final sorted = List<ProductCatalogItem>.from(published);
        sorted.sort((a, b) {
          final sa = displayConfigs[a.productCode]?.sortOrder ?? 999;
          final sb = displayConfigs[b.productCode]?.sortOrder ?? 999;
          return sa.compareTo(sb);
        });

        final items = sorted.map((p) {
          final cfg = displayConfigs[p.productCode];
          return p.toAssetsBundleItem(
            () => _onProductTap(p),
            overrideImageUrl: cfg?.headerMediaUrl,
            overrideTitle: cfg?.cardTitle,
            performance1d: cfg?.performance1d,
            onInvestTap: () => _onInvestTap(p),
          );
        }).toList();
        setState(() {
          _items = items;
          _showImageOverlay = false;
          _loading = false;
          _error = null;
        });
        return;
      }

      // 2) Fallback : widget crypto-bundles (CMS)
      final sections = await _vaultsApi.getMarketingCardsSectionsFromWidget(_widgetSlug);
      if (!mounted) return;
      final items = <AssetsBundleItem>[];

      bool showImageOverlay = false;
      for (final section in sections) {
        if (section.assetsBundleItems.isNotEmpty) {
          if (items.isEmpty) showImageOverlay = section.showImageOverlay ?? false;
          for (final bundle in section.assetsBundleItems) {
            items.add(bundle.toAssetsBundleItem(_onRedirect));
          }
        }
      }

      if (items.isEmpty) {
        for (final section in sections) {
          if (section.items.isNotEmpty) {
            for (final config in section.items) {
              items.add(AssetsBundleItem(
                imageUrl: config.imageUrl,
                title: config.title?.trim().isNotEmpty == true ? config.title! : 'Bundle',
                description: config.description,
                performance24h: null,
                cryptoIcons: const [Icons.currency_bitcoin],
                onTap: () => _onRedirect(config.redirectUrl),
              ));
            }
            break;
          }
        }
      }

      setState(() {
        _items = items;
        _showImageOverlay = items.isNotEmpty ? showImageOverlay : false;
        _loading = false;
        _error = null;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _items = const [];
        _loading = false;
        _error = e.toString();
      });
    }
  }

  void _onProductTap(ProductCatalogItem product) {
    _onRedirect('product://${product.productCode}');
  }

  Future<void> _onInvestTap(ProductCatalogItem product) async {
    String? portfolioId = product.portfolioId;

    if (portfolioId == null || portfolioId.isEmpty) {
      try {
        final enriched = await _catalogApi.getBundleCatalog();
        final match = enriched.where((p) => p.id == product.id).toList();
        if (match.isNotEmpty) {
          portfolioId = match.first.portfolioId;
        }
      } catch (_) {}
    }

    if (!mounted) return;

    if (portfolioId == null || portfolioId.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Ce bundle n\'est pas encore disponible à l\'investissement.'),
          duration: Duration(seconds: 3),
        ),
      );
      return;
    }

    final bundle = BundleItem(
      portfolioId: portfolioId,
      productId: product.id,
      name: product.name,
      description: product.description ?? product.allocationsSummary,
      entryAssetDefault: product.entryAssetDefault ?? 'USDC',
      entryAssetsAllowed: product.entryAssetsAllowed ?? ['USDC'],
      allocations: product.allocations
          .map((a) => BundleAllocationTarget(
                asset: a.assetSymbol,
                weight: a.targetWeight,
              ))
          .toList(),
    );
    final didInvest = await BundleInvestFlowController.start(context, bundle: bundle);
    if (didInvest == true && mounted) {
      _load();
    }
  }

  Future<void> _onRedirect(String redirectUrl) async {
    final raw = redirectUrl.trim();
    if (raw.startsWith('vault://')) {
      final slug = raw.substring('vault://'.length).trim();
      if (slug.isNotEmpty) {
        await VaultPreviewScreen.open(context, slug);
      }
      return;
    }
    if (raw.startsWith('product://')) {
      final productId = raw.substring('product://'.length).trim();
      if (productId.isNotEmpty && mounted) {
        await ProductPreviewScreen.open(context, productId);
      }
      return;
    }
    if (raw.startsWith('blog://')) {
      // Optionnel : ouvrir article si besoin
      return;
    }
    if (raw.startsWith('bundle://')) {
      return;
    }
    if (raw.startsWith('/')) {
      final uri = Uri.tryParse(raw);
      final slug = uri?.pathSegments.isNotEmpty == true
          ? uri!.pathSegments.last.trim()
          : '';
      if (slug.isNotEmpty) {
        await VaultPreviewScreen.open(context, slug);
        return;
      }
    }
    final uri = Uri.tryParse(
      redirectUrl.startsWith('http') ? redirectUrl : 'https://$redirectUrl',
    );
    if (uri == null) return;
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: AppSpacing.xl),
        child: Center(child: CircularProgressIndicator()),
      );
    }
    if (_error != null) {
      return Padding(
        padding: const EdgeInsets.all(AppSpacing.xl),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              _error!,
              style: AppTypography.bodySmall.copyWith(color: AppColors.errorText),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: AppSpacing.md),
            TextButton.icon(
              onPressed: _load,
              icon: const Icon(Icons.refresh, size: 18),
              label: const Text('Réessayer'),
            ),
          ],
        ),
      );
    }
    if (_items.isEmpty) {
      return const SizedBox.shrink();
    }
    return AssetsBundlesModule(
      title: widget.title,
      items: _items,
      visibleCardsCount: 1.4,
      showImageOverlay: _showImageOverlay,
    );
  }
}
