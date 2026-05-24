import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../core/config.dart';
import '../../../core/locale_preference.dart';
import '../../../core/session_bearer_http.dart';
import '../domain/models/offer_project.dart';

class OffersApiException implements Exception {
  final int statusCode;
  final String message;

  OffersApiException(this.statusCode, this.message);

  @override
  String toString() => 'OffersApiException($statusCode): $message';
}

/// API **legacy** : liste projets CMS via GET /api/projects.
///
/// Phase 8 — Ce n’est plus la source canonique des Exclusive Offers (voir [CatalogApi] +
/// `/api/mobile/flutter/catalog/products`). Conservé pour repli Flutter, catégories
/// d’investissement, et tout autre appel encore nécessaire tant que [Config.projectsUrl]
/// est exposé.
class OffersApi {
  final String baseUrl;

  OffersApi({String? baseUrl}) : baseUrl = baseUrl ?? Config.apiBaseUrl;

  Future<Map<String, String>> _headers(Uri uri, String tag) =>
      SessionBearerHttp.jsonHeadersAppScoped(uri: uri, debugTag: tag);

  /// Récupère la liste des projets publiés (image, titre, catégorie).
  Future<List<OfferProject>> getProjects({String? locale, int limit = 50}) async {
    final effectiveLocale = LocalePreference.instance.resolve(locale);
    final uri = Uri.parse(Config.projectsUrl).replace(
      queryParameters: {
        'locale': effectiveLocale,
        'limit': limit.toString(),
      },
    );

    final response = await http.get(
      uri,
      headers: await _headers(uri, 'OffersApi.getProjects'),
    );

    if (response.statusCode != 200) {
      throw OffersApiException(
        response.statusCode,
        response.body.isNotEmpty ? response.body : 'Erreur réseau',
      );
    }

    final json = jsonDecode(response.body) as Map<String, dynamic>;
    final list = json['projects'] as List<dynamic>? ?? [];
    return list
        .map((e) {
          final rawSlug = (e['slug'] as String?)?.trim();
          return OfferProject(
              id: e['id'] as String,
              imageUrl: e['coverUrl'] as String? ?? '',
              title: e['title'] as String? ?? '',
              category: e['category'] as String? ?? 'Real estate',
              shortDescription: e['shortDescription'] as String?,
              description: e['description'] as String?,
              descriptionLinks: e['descriptionLinks'] is List
                  ? (e['descriptionLinks'] as List)
                      .whereType<Map>()
                      .map((item) => Map<String, dynamic>.from(item))
                      .toList()
                  : null,
              howItWorks: e['howItWorks'] is Map<String, dynamic>
                  ? e['howItWorks'] as Map<String, dynamic>
                  : null,
              keyInformation: e['keyInformation'] is Map<String, dynamic>
                  ? e['keyInformation'] as Map<String, dynamic>
                  : null,
              teaserVideoUrl: e['teaserVideoUrl'] as String?,
              promoVideoUrls: e['promoVideoUrls'] is List
                  ? (e['promoVideoUrls'] as List)
                      .map((a) => a.toString())
                      .where((s) => s.trim().isNotEmpty)
                      .toList()
                  : const [],
              hasGallery: e['hasGallery'] as bool? ?? false,
              competitiveAdvantages: e['competitiveAdvantages'] is Map<String, dynamic>
                  ? e['competitiveAdvantages'] as Map<String, dynamic>
                  : null,
              faq: e['faq'] is Map<String, dynamic>
                  ? e['faq'] as Map<String, dynamic>
                  : null,
              apy: (e['apy'] as num?)?.toDouble(),
              raised: (e['raised'] as num?)?.toDouble(),
              target: (e['target'] as num?)?.toDouble(),
              progress: (e['progress'] as num?)?.toDouble(),
              investorsCount: (e['investorsCount'] as num?)?.toInt(),
              durationMonths: (e['durationMonths'] as num?)?.toInt(),
              lendingAsset: e['lendingAsset'] as String?,
              lendingStatus: e['lendingStatus'] as String?,
              isInvestable: e['isInvestable'] as bool? ?? false,
              lendingProductId: e['lendingProductId'] as String?,
              entryAssetDefault: e['entryAssetDefault'] as String?,
              entryAssetsAllowed: (e['entryAssetsAllowed'] as List<dynamic>?)
                  ?.map((a) => a.toString())
                  .toList(),
              /// Slug page CMS — pour offres `eo-…` alignées sur le registre, permet le même
              /// chargement détail que le catalogue (`GET …/catalog/products/{slug}`).
              catalogSlug: (rawSlug != null && rawSlug.isNotEmpty) ? rawSlug : null,
              vaultHeroTags: const [],
              vaultFunding: null,
            );
        })
        .toList();
  }

  /// Récupère les catégories d'investissement (pour le widget au-dessus des offres).
  Future<List<InvestmentCategory>> getInvestmentCategories() async {
    final uri = Uri.parse(Config.investmentCategoriesUrl);
    final response = await http.get(
      uri,
      headers: await _headers(uri, 'OffersApi.getInvestmentCategories'),
    );
    if (response.statusCode != 200) {
      throw OffersApiException(
        response.statusCode,
        response.body.isNotEmpty ? response.body : 'Erreur réseau',
      );
    }
    final json = jsonDecode(response.body) as Map<String, dynamic>;
    final list = json['categories'] as List<dynamic>? ?? [];
    return list
        .map((e) => InvestmentCategory(
              id: e['id'] as String,
              slug: e['slug'] as String,
              label: e['label'] as String,
              imageUrl: e['imageUrl'] as String?,
            ))
        .toList();
  }
}

/// Catégorie d'investissement (API /api/investment-categories).
class InvestmentCategory {
  final String id;
  final String slug;
  final String label;
  final String? imageUrl;

  InvestmentCategory({
    required this.id,
    required this.slug,
    required this.label,
    this.imageUrl,
  });
}
