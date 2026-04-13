import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import '../../../../core/config.dart';
import '../../../../core/session_bearer_http.dart';
import '../../../../design_system/design_system.dart';
import '../../../favorites/data/favorites_api.dart';
import '../../../landing_preview/data/landing_page_builder_api.dart';
import '../../../landing_preview/presentation/screens/landing_page_preview_screen.dart';
import '../../data/product_catalog_api.dart';
import '../../../wallet/presentation/screens/bundle_invest_flow/bundle_invest_flow_controller.dart';

/// Écran de détail d'un produit Portfolio Engine.
/// Charge la config du builder (modules, headerMedia) depuis l'API Next.js
/// et l'affiche via [LandingPagePreviewScreen] (même template que les Vaults).
class ProductPreviewScreen extends StatefulWidget {
  const ProductPreviewScreen({super.key, required this.productId});

  final String productId;

  static Future<void> open(BuildContext context, String productId) {
    return Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (_) => ProductPreviewScreen(productId: productId),
      ),
    );
  }

  @override
  State<ProductPreviewScreen> createState() => _ProductPreviewScreenState();
}

class _ProductPreviewScreenState extends State<ProductPreviewScreen> {
  final ProductCatalogApi _catalogApi = ProductCatalogApi();
  final FavoritesApi _favoritesApi = FavoritesApi();

  bool _loading = true;
  String? _error;
  LandingPagePayload? _payload;
  ProductDetailItem? _productDetail;
  String? _resolvedPortfolioId;
  /// Allocations pour le hero (GET détail puis catalogue bundle si vide).
  List<ProductAllocationSummary>? _bundleAllocationsForHero;
  /// Déduit du `product_type` API et, si absent, du catalogue bundle (GET détail peut être null).
  bool _isCryptoBundleProduct = false;
  bool _isFavorite = false;
  String? _favoriteId;

  @override
  void initState() {
    super.initState();
    _load();
    _loadFavoriteStatus();
  }

  Future<void> _loadFavoriteStatus() async {
    try {
      final favs = await _favoritesApi.fetchFavorites(entityType: 'bundle');
      if (!mounted) return;
      final match = favs.where((f) => f.entityId == widget.productId).toList();
      setState(() {
        _isFavorite = match.isNotEmpty;
        _favoriteId = match.isNotEmpty ? match.first.id : null;
      });
    } catch (_) {}
  }

  Future<void> _toggleFavorite() async {
    if (_isFavorite && _favoriteId != null) {
      final ok = await _favoritesApi.removeFavorite(_favoriteId!);
      if (ok && mounted) {
        setState(() {
          _isFavorite = false;
          _favoriteId = null;
        });
      }
    } else {
      final result = await _favoritesApi.addFavorite(
        entityType: 'bundle',
        entityId: widget.productId,
      );
      if (result.isSuccess && result.favorite != null && mounted) {
        setState(() {
          _isFavorite = true;
          _favoriteId = result.favorite!.id;
        });
      } else if (!result.isSuccess && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(result.messageForUser()),
            duration: const Duration(seconds: 3),
          ),
        );
      }
    }
  }

  /// True si produit bundle : type API `crypto_bundle`, ou type absent / détail null et id présent dans le catalogue bundle.
  Future<bool> _resolveIsCryptoBundleProduct(ProductDetailItem? detail) async {
    final t = (detail?.productType ?? '').trim().toLowerCase();
    if (t == 'crypto_bundle') return true;
    if (detail != null && t.isNotEmpty) return false;
    try {
      final bundles = await _catalogApi.getBundleCatalog();
      final id = widget.productId.trim();
      return bundles.any((b) => b.id == id || b.productCode == id);
    } catch (_) {
      return false;
    }
  }

  /// Détail produit puis [getBundleCatalog] — le GET `/detail` n’expose pas toujours les allocations.
  Future<List<ProductAllocationSummary>?> _resolveBundleAllocationsForHero(
    ProductDetailItem? detail,
  ) async {
    final fromDetail = detail?.allocations;
    if (fromDetail != null && fromDetail.isNotEmpty) return fromDetail;
    try {
      final cat = await _catalogApi.getBundleCatalog();
      final id = widget.productId.trim();
      for (final p in cat) {
        if (p.id == id || p.productCode == id) {
          if (p.allocations.isNotEmpty) return p.allocations;
          break;
        }
      }
    } catch (_) {}
    return null;
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final results = await Future.wait([
        _fetchProductConfig(widget.productId),
        _catalogApi.getProductDetail(widget.productId),
        _resolvePortfolioId(widget.productId),
      ]);
      if (!mounted) return;
      final payload = results[0] as LandingPagePayload;
      final detail = results[1] as ProductDetailItem?;
      final resolvedPid = results[2] as String?;
      final isBundle = await _resolveIsCryptoBundleProduct(detail);
      final heroAlloc =
          isBundle ? await _resolveBundleAllocationsForHero(detail) : null;
      if (!mounted) return;
      setState(() {
        _payload = payload;
        _productDetail = detail;
        _resolvedPortfolioId = resolvedPid;
        _isCryptoBundleProduct = isBundle;
        _bundleAllocationsForHero = heroAlloc;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  Future<String?> _resolvePortfolioId(String productId) async {
    try {
      final items = await _catalogApi.getBundleCatalog();
      final match = items.where((p) =>
          p.id == productId || p.productCode == productId).toList();
      if (match.isNotEmpty) return match.first.portfolioId;
    } catch (_) {}
    return null;
  }

  Future<LandingPagePayload> _fetchProductConfig(String productId) async {
    final uri = Uri.parse(Config.portfolioProductUrl(productId));
    final response = await http.get(
      uri,
      headers: await SessionBearerHttp.jsonHeadersAppScoped(
        uri: uri,
        debugTag: 'ProductPreviewScreen._fetchProductConfig',
      ),
    );
    if (response.statusCode != 200) {
      throw LandingPageBuilderApiException(
        response.statusCode,
        response.body.isNotEmpty ? response.body : 'Erreur réseau',
      );
    }
    final json = jsonDecode(response.body) as Map<String, dynamic>;
    final page = json['page'];
    final vault = json['vault'];
    if (page is! Map<String, dynamic> || vault is! Map<String, dynamic>) {
      throw LandingPageBuilderApiException(500, 'Payload produit invalide');
    }
    return LandingPagePayload(
      slug: (page['slug'] ?? '').toString(),
      title: page['title']?.toString(),
      description: page['description']?.toString(),
      config: Map<String, dynamic>.from(vault),
    );
  }

  String? get _effectivePortfolioId {
    final fromDetail = _productDetail?.portfolioId;
    if (fromDetail != null && fromDetail.isNotEmpty) return fromDetail;
    return _resolvedPortfolioId;
  }

  Future<void> _onInvestTap() async {
    final detail = _productDetail;
    if (detail == null) return;

    String? portfolioId = _effectivePortfolioId;

    if (portfolioId == null || portfolioId.isEmpty) {
      portfolioId = await _resolvePortfolioId(widget.productId);
      if (portfolioId != null && portfolioId.isNotEmpty && mounted) {
        setState(() => _resolvedPortfolioId = portfolioId);
      }
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
      productId: detail.id,
      name: detail.name,
      description: detail.description ?? detail.allocationsSummary,
      entryAssetDefault: detail.entryAssetDefault ?? 'USDC',
      entryAssetsAllowed: detail.entryAssetsAllowed ?? ['USDC'],
      allocations: detail.allocations
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

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Scaffold(
        backgroundColor: AppColors.pageBackground,
        body: Center(child: CircularProgressIndicator()),
      );
    }
    if (_error != null) {
      return Scaffold(
        backgroundColor: AppColors.pageBackground,
        appBar: AppBar(
          title: const Text('Produit'),
          leading: IconButton(
            icon: const Icon(Icons.arrow_back),
            onPressed: () => Navigator.of(context).pop(),
          ),
        ),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(AppSpacing.xl),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  _error!,
                  style: AppTypography.bodyMedium.copyWith(color: AppColors.errorText),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: AppSpacing.lg),
                TextButton.icon(
                  onPressed: _load,
                  icon: const Icon(Icons.refresh, size: 20),
                  label: const Text('Réessayer'),
                ),
              ],
            ),
          ),
        ),
      );
    }
    if (_payload != null) {
      return LandingPagePreviewScreen(
        initialSlug: widget.productId,
        preloadedPayload: _payload,
        controlsEnabled: false,
        onRefresh: _load,
        onInvestTap: _isCryptoBundleProduct ? _onInvestTap : null,
        useImmersiveExclusiveTemplate: _isCryptoBundleProduct,
        bundleAllocations: _bundleAllocationsForHero,
        extraNavBarActions: [
          AppTopNavBarAction(
            icon: _isFavorite ? Icons.star_rounded : Icons.star_outline,
            iconColor: _isFavorite ? const Color(0xFFFFB800) : null,
            onPressed: _toggleFavorite,
          ),
        ],
      );
    }
    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      body: const Center(child: Text('Produit introuvable')),
    );
  }
}
