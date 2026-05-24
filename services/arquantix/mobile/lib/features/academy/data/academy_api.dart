import 'dart:convert';
import 'dart:async';
import 'dart:io';

import 'package:http/http.dart' as http;

import '../../../core/config.dart';
import '../../../core/locale_preference.dart';
import '../domain/models/academy_center_models.dart';

class AcademyApiException implements Exception {
  AcademyApiException(this.statusCode, this.message);

  final int statusCode;
  final String message;

  @override
  String toString() => 'AcademyApiException($statusCode): $message';
}

/// Client HTTP du module Academy. Mêmes principes que [HelpApi] : retry
/// 3 attempts avec backoff sur SocketException / TimeoutException, timeout
/// 8 s par requête, base URL via [Config.apiBaseUrl].
class AcademyApi {
  AcademyApi({String? baseUrl}) : baseUrl = baseUrl ?? Config.apiBaseUrl;

  final String baseUrl;

  Future<http.Response> _getWithRetry(Uri uri) async {
    const maxAttempts = 3;
    Object? lastError;
    for (var attempt = 1; attempt <= maxAttempts; attempt++) {
      try {
        return await http.get(uri).timeout(const Duration(seconds: 8));
      } on SocketException catch (e) {
        lastError = e;
      } on TimeoutException catch (e) {
        lastError = e;
      }
      if (attempt < maxAttempts) {
        await Future<void>.delayed(Duration(milliseconds: 250 * attempt));
      }
    }
    throw AcademyApiException(
      0,
      'Connexion impossible vers $uri (${lastError ?? 'erreur réseau'})',
    );
  }

  Future<List<AcademyCollectionItem>> getCollections({String? locale}) async {
    final effectiveLocale = LocalePreference.instance.resolve(locale);
    final uri = Uri.parse(Config.academyCollectionsUrl).replace(
      queryParameters: {'locale': effectiveLocale},
    );
    final response = await _getWithRetry(uri);
    if (response.statusCode != 200) {
      throw AcademyApiException(
        response.statusCode,
        response.body.isNotEmpty ? response.body : 'Erreur réseau',
      );
    }
    final json = jsonDecode(response.body) as Map<String, dynamic>;
    final list = (json['collections'] as List<dynamic>? ?? const []);
    return list
        .whereType<Map<String, dynamic>>()
        .map(AcademyCollectionItem.fromJson)
        .where((item) => item.slug.isNotEmpty && item.title.isNotEmpty)
        .toList();
  }

  Future<AcademyCategoryListResponse> getCategories({
    required String collectionSlug,
    String? locale,
  }) async {
    final effectiveLocale = LocalePreference.instance.resolve(locale);
    final uri = Uri.parse(
      Config.academyCollectionCategoriesUrl(collectionSlug),
    ).replace(queryParameters: {'locale': effectiveLocale});
    final response = await _getWithRetry(uri);
    if (response.statusCode != 200) {
      throw AcademyApiException(
        response.statusCode,
        response.body.isNotEmpty ? response.body : 'Erreur réseau',
      );
    }
    final json = jsonDecode(response.body) as Map<String, dynamic>;
    return AcademyCategoryListResponse.fromJson(json);
  }

  Future<AcademyArticleListResponse> getArticles({
    required String collectionSlug,
    required String categorySlug,
    String? locale,
  }) async {
    final effectiveLocale = LocalePreference.instance.resolve(locale);
    final uri = Uri.parse(
      Config.academyCategoryArticlesUrl(collectionSlug, categorySlug),
    ).replace(queryParameters: {'locale': effectiveLocale});
    final response = await _getWithRetry(uri);
    if (response.statusCode != 200) {
      throw AcademyApiException(
        response.statusCode,
        response.body.isNotEmpty ? response.body : 'Erreur réseau',
      );
    }
    final json = jsonDecode(response.body) as Map<String, dynamic>;
    return AcademyArticleListResponse.fromJson(json);
  }

  /// Récupère un article Academy par son slug global (premier publié).
  Future<AcademyArticleDetail?> getArticleBySlug(String slug, {String? locale}) async {
    final effectiveLocale = LocalePreference.instance.resolve(locale);
    final uri = Uri.parse(Config.academyArticleBySlugUrl).replace(
      queryParameters: {'slug': slug, 'locale': effectiveLocale},
    );
    final response = await _getWithRetry(uri);
    if (response.statusCode == 404) return null;
    if (response.statusCode != 200) {
      throw AcademyApiException(
        response.statusCode,
        response.body.isNotEmpty ? response.body : 'Erreur réseau',
      );
    }
    final json = jsonDecode(response.body) as Map<String, dynamic>;
    final article = json['article'] as Map<String, dynamic>?;
    if (article == null) return null;
    return AcademyArticleDetail.fromJson(article);
  }

  Future<AcademyArticleDetail> getArticleDetail({
    required String collectionSlug,
    required String categorySlug,
    required String articleSlug,
    String? locale,
  }) async {
    final effectiveLocale = LocalePreference.instance.resolve(locale);
    final uri = Uri.parse(
      Config.academyArticleDetailUrl(collectionSlug, categorySlug, articleSlug),
    ).replace(queryParameters: {'locale': effectiveLocale});
    final response = await _getWithRetry(uri);
    if (response.statusCode != 200) {
      throw AcademyApiException(
        response.statusCode,
        response.body.isNotEmpty ? response.body : 'Erreur réseau',
      );
    }
    final json = jsonDecode(response.body) as Map<String, dynamic>;
    return AcademyArticleDetail.fromJson(
      (json['article'] as Map<String, dynamic>? ?? const {}),
    );
  }

  Future<List<AcademyTaggedArticleItem>> getArticlesByTag({
    required String tagType,
    required String tagId,
    String? locale,
  }) async {
    final effectiveLocale = LocalePreference.instance.resolve(locale);
    final uri = Uri.parse(Config.academyArticlesByTagUrl).replace(
      queryParameters: {
        'type': tagType,
        'id': tagId,
        'locale': effectiveLocale,
      },
    );
    final response = await _getWithRetry(uri);
    if (response.statusCode != 200) {
      throw AcademyApiException(
        response.statusCode,
        response.body.isNotEmpty ? response.body : 'Erreur réseau',
      );
    }
    final json = jsonDecode(response.body) as Map<String, dynamic>;
    final list = (json['articles'] as List<dynamic>? ?? const []);
    return list
        .whereType<Map<String, dynamic>>()
        .map(AcademyTaggedArticleItem.fromJson)
        .where(
          (item) =>
              item.slug.isNotEmpty &&
              item.question.isNotEmpty &&
              item.collectionSlug.isNotEmpty &&
              item.categorySlug.isNotEmpty,
        )
        .toList();
  }
}
