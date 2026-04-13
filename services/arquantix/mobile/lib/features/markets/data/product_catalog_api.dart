import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import '../../../core/config.dart';
import '../../../core/session_bearer_http.dart';
import '../../../design_system/components/assets_bundles_module.dart';

/// API du catalogue produits Portfolio Engine (GET /api/portfolio-engine/products/catalog).
/// Utilise la même base URL que market-data (FastAPI port 8000).
class ProductCatalogApi {
  ProductCatalogApi({String? baseUrl})
      : _baseUrl = baseUrl ?? Config.marketDataBaseUrl;

  final String _baseUrl;

  Future<Map<String, String>> _flutterBffHeaders(Uri uri, String tag) =>
      SessionBearerHttp.jsonHeadersAppScoped(uri: uri, debugTag: tag);

  static String get _catalogPath => '/api/portfolio-engine/product-catalog';

  String get _catalogUrl {
    final base = _baseUrl.endsWith('/') ? _baseUrl.substring(0, _baseUrl.length - 1) : _baseUrl;
    return '$base$_catalogPath';
  }

  /// Charge le détail d'un produit (GET /api/portfolio-engine/products/{id}/detail).
  Future<ProductDetailItem?> getProductDetail(String productId) async {
    final id = productId.trim();
    if (id.isEmpty) return null;
    final base = _baseUrl.endsWith('/') ? _baseUrl.substring(0, _baseUrl.length - 1) : _baseUrl;
    final uri = Uri.parse('$base/api/portfolio-engine/products/$id/detail');
    final response = await http.get(uri);
    if (response.statusCode != 200) return null;
    final json = jsonDecode(response.body) as Map<String, dynamic>;
    return ProductDetailItem.fromJson(json);
  }

  /// Charge les configs d'affichage (image header + titre card) depuis le builder admin.
  /// Retourne un Map<productCode, ProductDisplayConfig>.
  Future<Map<String, ProductDisplayConfig>> getDisplayConfigs() async {
    try {
      final base = Config.apiBaseUrl.endsWith('/')
          ? Config.apiBaseUrl.substring(0, Config.apiBaseUrl.length - 1)
          : Config.apiBaseUrl;
      final uri = Uri.parse('$base/api/mobile/flutter/portfolio-products/configs');
      final response = await http.get(
        uri,
        headers: await _flutterBffHeaders(uri, 'ProductCatalogApi.getDisplayConfigs'),
      );
      if (response.statusCode != 200) return {};
      final json = jsonDecode(response.body) as Map<String, dynamic>;
      final configs = json['configs'] as Map<String, dynamic>? ?? {};
      return configs.map(
        (key, value) => MapEntry(
          key,
          ProductDisplayConfig.fromJson(
            value is Map<String, dynamic> ? value : {},
          ),
        ),
      );
    } catch (e) {
      debugPrint('[ProductCatalogApi] getDisplayConfigs error: $e');
      return {};
    }
  }

  /// Charge le catalogue des produits investissables (publics, actifs).
  /// Retourne une liste de [ProductCatalogItem] mappables en [AssetsBundleItem].
  Future<List<ProductCatalogItem>> getCatalog({
    String? productType,
  }) async {
    final uri = productType != null && productType.trim().isNotEmpty
        ? Uri.parse(_catalogUrl).replace(
            queryParameters: {'product_type': productType.trim()},
          )
        : Uri.parse(_catalogUrl);

    final response = await http.get(uri);
    if (response.statusCode != 200) {
      throw ProductCatalogApiException(
        response.statusCode,
        response.body.isNotEmpty ? response.body : 'Erreur réseau',
      );
    }

    final json = jsonDecode(response.body) as Map<String, dynamic>;
    final itemsRaw = json['items'] as List<dynamic>? ?? [];
    return itemsRaw
        .whereType<Map>()
        .map((m) => ProductCatalogItem.fromJson(m.cast<String, dynamic>()))
        .toList();
  }

  /// Charge le catalogue bundle enrichi avec les portfolio IDs du client.
  /// Endpoint : GET /api/app/bundle/catalog (via proxy Next.js).
  Future<List<ProductCatalogItem>> getBundleCatalog() async {
    final uri = Uri.parse(Config.bundleCatalogUrl);
    final response = await http.get(
      uri,
      headers: await _flutterBffHeaders(uri, 'ProductCatalogApi.getBundleCatalog'),
    );
    if (response.statusCode != 200) {
      throw ProductCatalogApiException(
        response.statusCode,
        response.body.isNotEmpty ? response.body : 'Erreur réseau',
      );
    }
    final json = jsonDecode(response.body) as Map<String, dynamic>;
    final itemsRaw = json['items'] as List<dynamic>? ?? [];
    return itemsRaw
        .whereType<Map>()
        .map((m) => ProductCatalogItem.fromJson(m.cast<String, dynamic>()))
        .toList();
  }
}

/// Config d'affichage (image + titre) définie dans le builder admin.
class ProductDisplayConfig {
  const ProductDisplayConfig({
    this.headerMediaUrl,
    this.detailMediaUrl,
    this.cardTitle,
    this.sortOrder = 999,
    this.performance1d,
  });

  /// Background image for the card widget (Crypto Bundles list).
  final String? headerMediaUrl;

  /// Background image for the detail page hero (LayoutPageLevel2).
  final String? detailMediaUrl;

  final String? cardTitle;
  final int sortOrder;

  /// 1-day performance percentage from chart-history (e.g. 2.45 or -0.32).
  final double? performance1d;

  static ProductDisplayConfig fromJson(Map<String, dynamic> json) {
    return ProductDisplayConfig(
      headerMediaUrl: (json['headerMediaUrl'] ?? '').toString().trim().isEmpty
          ? null
          : json['headerMediaUrl'].toString().trim(),
      detailMediaUrl: (json['detailMediaUrl'] ?? '').toString().trim().isEmpty
          ? null
          : json['detailMediaUrl'].toString().trim(),
      cardTitle: (json['cardTitle'] ?? '').toString().trim().isEmpty
          ? null
          : json['cardTitle'].toString().trim(),
      sortOrder: (json['sortOrder'] as num?)?.toInt() ?? 999,
      performance1d: (json['performance1d'] is num)
          ? (json['performance1d'] as num).toDouble()
          : null,
    );
  }
}

class ProductCatalogApiException implements Exception {
  ProductCatalogApiException(this.statusCode, this.message);

  final int statusCode;
  final String message;

  @override
  String toString() => 'ProductCatalogApiException($statusCode): $message';
}

/// Item produit du catalogue.
class ProductCatalogItem {
  const ProductCatalogItem({
    required this.id,
    required this.productCode,
    required this.name,
    this.description,
    required this.productType,
    this.riskLabel,
    required this.baseCurrency,
    required this.allocations,
    required this.availableRebalanceFrequencies,
    this.portfolioId,
    this.status,
    this.entryAssetDefault,
    this.entryAssetsAllowed,
  });

  final String id;
  final String productCode;
  final String name;
  final String? description;
  final String productType;
  final String? riskLabel;
  final String baseCurrency;
  final List<ProductAllocationSummary> allocations;
  final List<String> availableRebalanceFrequencies;
  final String? portfolioId;
  final String? status;
  final String? entryAssetDefault;
  final List<String>? entryAssetsAllowed;

  static ProductCatalogItem fromJson(Map<String, dynamic> json) {
    final allocsRaw = json['allocations'] as List<dynamic>? ?? [];
    final allocs = allocsRaw
        .whereType<Map>()
        .map((m) => ProductAllocationSummary.fromJson(m.cast<String, dynamic>()))
        .toList();
    final freqRaw = json['available_rebalance_frequencies'] as List<dynamic>? ?? [];
    final freqs = freqRaw
        .whereType<String>()
        .map((s) => s.toString().trim())
        .where((s) => s.isNotEmpty)
        .toList();
    final meta = json['metadata'] as Map<String, dynamic>? ?? {};

    final entryAllowedRaw =
        json['entry_assets_allowed'] as List<dynamic>? ??
        meta['entry_assets_allowed'] as List<dynamic>?;

    final entryDefault =
        _nonEmpty(json['entry_asset_default']) ??
        _nonEmpty(meta['entry_asset_default']);

    return ProductCatalogItem(
      id: (json['id'] ?? '').toString().trim(),
      productCode: (json['product_code'] ?? '').toString().trim(),
      name: (json['name'] ?? '').toString().trim(),
      description: (json['description'] ?? '').toString().trim().isEmpty
          ? null
          : (json['description'] ?? '').toString().trim(),
      productType: (json['product_type'] ?? '').toString().trim(),
      riskLabel: (json['risk_label'] ?? '').toString().trim().isEmpty
          ? null
          : (json['risk_label'] ?? '').toString().trim(),
      baseCurrency: (json['base_currency'] ?? 'USD').toString().trim(),
      allocations: allocs,
      availableRebalanceFrequencies: freqs,
      portfolioId: _nonEmpty(json['portfolio_id']),
      status: _nonEmpty(json['status']),
      entryAssetDefault: entryDefault,
      entryAssetsAllowed: entryAllowedRaw
          ?.whereType<String>()
          .map((s) => s.trim())
          .where((s) => s.isNotEmpty)
          .toList(),
    );
  }

  static String? _nonEmpty(dynamic v) {
    if (v == null) return null;
    final s = v.toString().trim();
    return s.isEmpty ? null : s;
  }

  /// Résumé des allocations (ex: "BTC 70% / ETH 30%").
  String get allocationsSummary {
    if (allocations.isEmpty) return '';
    return allocations
        .map((a) => '${a.assetSymbol} ${(a.targetWeight * 100).toStringAsFixed(0)}%')
        .join(' / ');
  }

  /// Convertit en [AssetsBundleItem] pour [AssetsBundlesModule].
  /// [overrideImageUrl] et [overrideTitle] permettent de remplacer l'image/titre
  /// par ceux définis dans le builder admin (portfolio product config).
  AssetsBundleItem toAssetsBundleItem(
    VoidCallback onTap, {
    String? overrideImageUrl,
    String? overrideTitle,
    double? performance1d,
    VoidCallback? onInvestTap,
  }) {
    final sortedAllocs = List<ProductAllocationSummary>.from(allocations)
      ..sort((a, b) => a.targetWeight.compareTo(b.targetWeight));
    final tickers = sortedAllocs
        .map((a) => a.assetSymbol.trim().toUpperCase())
        .where((s) => s.isNotEmpty)
        .toList();
    final iconCount = tickers.isEmpty ? 2 : tickers.length;
    final effectiveImage = (overrideImageUrl != null && overrideImageUrl.trim().isNotEmpty)
        ? overrideImageUrl
        : '';
    final effectiveTitle = (overrideTitle != null && overrideTitle.trim().isNotEmpty)
        ? overrideTitle
        : name;
    return AssetsBundleItem(
      imageUrl: effectiveImage,
      title: effectiveTitle,
      description: description ?? allocationsSummary,
      performance24h: performance1d,
      cryptoIcons: List<IconData>.filled(iconCount, Icons.currency_bitcoin),
      cryptoTickers: tickers,
      onTap: onTap,
      onInvestTap: onInvestTap,
    );
  }
}

/// Détail produit (réponse GET /products/{id}/detail).
class ProductDetailItem extends ProductCatalogItem {
  const ProductDetailItem({
    required super.id,
    required super.productCode,
    required super.name,
    super.description,
    required super.productType,
    super.riskLabel,
    required super.baseCurrency,
    required super.allocations,
    required super.availableRebalanceFrequencies,
    super.portfolioId,
    super.entryAssetDefault,
    super.entryAssetsAllowed,
    this.templateId,
    this.templateCode,
    this.isPublic = false,
    this.status = '',
  });

  final String? templateId;
  final String? templateCode;
  final bool isPublic;
  final String status;

  static ProductDetailItem fromJson(Map<String, dynamic> json) {
    final base = ProductCatalogItem.fromJson(json);
    return ProductDetailItem(
      id: base.id,
      productCode: base.productCode,
      name: base.name,
      description: base.description,
      productType: base.productType,
      riskLabel: base.riskLabel,
      baseCurrency: base.baseCurrency,
      allocations: base.allocations,
      availableRebalanceFrequencies: base.availableRebalanceFrequencies,
      portfolioId: base.portfolioId,
      entryAssetDefault: base.entryAssetDefault,
      entryAssetsAllowed: base.entryAssetsAllowed,
      templateId: (json['template_id'] ?? '').toString().trim().isEmpty
          ? null
          : (json['template_id'] ?? '').toString().trim(),
      templateCode: (json['template_code'] ?? '').toString().trim().isEmpty
          ? null
          : (json['template_code'] ?? '').toString().trim(),
      isPublic: json['is_public'] == true,
      status: (json['status'] ?? '').toString().trim(),
    );
  }
}

class ProductAllocationSummary {
  const ProductAllocationSummary({
    required this.instrumentId,
    required this.instrumentCode,
    required this.name,
    required this.assetSymbol,
    required this.targetWeight,
  });

  final String instrumentId;
  final String instrumentCode;
  final String name;
  final String assetSymbol;
  final double targetWeight;

  static ProductAllocationSummary fromJson(Map<String, dynamic> json) {
    final rawWeight = json['target_weight'];
    final weight = rawWeight is num
        ? rawWeight.toDouble()
        : double.tryParse(rawWeight?.toString() ?? '') ?? 0.0;
    return ProductAllocationSummary(
      instrumentId: (json['instrument_id'] ?? '').toString().trim(),
      instrumentCode: (json['instrument_code'] ?? '').toString().trim(),
      name: (json['instrument_name'] ?? '').toString().trim(),
      assetSymbol: (json['asset_symbol'] ?? '').toString().trim().toUpperCase(),
      targetWeight: weight,
    );
  }
}
