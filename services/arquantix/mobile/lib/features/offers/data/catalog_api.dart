import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../core/config.dart';
import '../../../core/session_bearer_http.dart';
import '../domain/models/catalog_product.dart';

class CatalogApiException implements Exception {
  CatalogApiException(this.statusCode, this.message);

  final int statusCode;
  final String message;

  @override
  String toString() => 'CatalogApiException($statusCode): $message';
}

/// Product Registry — GET /api/mobile/flutter/catalog/products*
class CatalogApi {
  CatalogApi({String? baseUrl}) : baseUrl = baseUrl ?? Config.apiBaseUrl;

  final String baseUrl;

  Future<Map<String, String>> _headers(Uri uri, String tag) =>
      SessionBearerHttp.jsonHeadersAppScoped(uri: uri, debugTag: tag);

  /// Liste catalogue (exclusive_offer par défaut côté app).
  ///
  /// [commercialStatus] / [visibility] : si non nulls et non vides, envoyés au BFF
  /// (`/api/mobile/flutter/catalog/products`). Sinon le serveur applique published + public.
  Future<List<CatalogListItem>> getProducts({
    String locale = 'fr',
    int limit = 50,
    bool includeEngineData = true,
    String? commercialStatus,
    String? visibility,
  }) async {
    final params = <String, String>{
      'type': 'exclusive_offer',
      'locale': locale,
      'limit': limit.toString(),
      'include_engine_data': includeEngineData ? 'true' : 'false',
    };
    final cs = commercialStatus?.trim();
    final vis = visibility?.trim();
    if (cs != null && cs.isNotEmpty) {
      params['commercialStatus'] = cs;
    }
    if (vis != null && vis.isNotEmpty) {
      params['visibility'] = vis;
    }

    final uri = Uri.parse(Config.catalogProductsUrl).replace(queryParameters: params);

    final response = await http.get(
      uri,
      headers: await _headers(uri, 'CatalogApi.getProducts'),
    );

    if (response.statusCode != 200) {
      throw CatalogApiException(
        response.statusCode,
        response.body.isNotEmpty ? response.body : 'Erreur réseau',
      );
    }

    final json = jsonDecode(response.body) as Map<String, dynamic>;
    final list = json['products'] as List<dynamic>? ?? [];
    return list
        .whereType<Map<String, dynamic>>()
        .map(CatalogListItem.fromJson)
        .toList();
  }

  /// Détail par slug packagé (registry).
  Future<CatalogProductDetail> getProductBySlug(
    String slug, {
    String locale = 'fr',
    bool includeEngineData = true,
  }) async {
    final uri = Uri.parse(Config.catalogProductDetailUrl(slug)).replace(
      queryParameters: {
        'locale': locale,
        'include_engine_data': includeEngineData ? '1' : '0',
      },
    );

    final response = await http.get(
      uri,
      headers: await _headers(uri, 'CatalogApi.getProductBySlug'),
    );

    if (response.statusCode == 404) {
      throw CatalogApiException(404, 'Produit catalogue introuvable');
    }
    if (response.statusCode != 200) {
      throw CatalogApiException(
        response.statusCode,
        response.body.isNotEmpty ? response.body : 'Erreur réseau',
      );
    }

    return CatalogProductDetail.parse(response.body);
  }
}
