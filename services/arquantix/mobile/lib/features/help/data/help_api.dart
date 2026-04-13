import 'dart:convert';
import 'dart:async';
import 'dart:io';

import 'package:http/http.dart' as http;

import '../../../core/config.dart';
import '../domain/models/help_center_models.dart';

class HelpApiException implements Exception {
  HelpApiException(this.statusCode, this.message);

  final int statusCode;
  final String message;

  @override
  String toString() => 'HelpApiException($statusCode): $message';
}

class HelpApi {
  HelpApi({String? baseUrl}) : baseUrl = baseUrl ?? Config.apiBaseUrl;

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
    throw HelpApiException(
      0,
      'Connexion impossible vers $uri (${lastError ?? 'erreur réseau'})',
    );
  }

  Future<List<HelpCollectionItem>> getCollections({String locale = 'fr'}) async {
    final uri = Uri.parse(Config.helpCollectionsUrl).replace(
      queryParameters: {'locale': locale},
    );
    final response = await _getWithRetry(uri);
    if (response.statusCode != 200) {
      throw HelpApiException(
        response.statusCode,
        response.body.isNotEmpty ? response.body : 'Erreur réseau',
      );
    }
    final json = jsonDecode(response.body) as Map<String, dynamic>;
    final list = (json['collections'] as List<dynamic>? ?? const []);
    return list
        .whereType<Map<String, dynamic>>()
        .map(HelpCollectionItem.fromJson)
        .where((item) => item.slug.isNotEmpty && item.title.isNotEmpty)
        .toList();
  }

  Future<HelpCategoryListResponse> getCategories({
    required String collectionSlug,
    String locale = 'fr',
  }) async {
    final uri = Uri.parse(
      Config.helpCollectionCategoriesUrl(collectionSlug),
    ).replace(queryParameters: {'locale': locale});
    final response = await _getWithRetry(uri);
    if (response.statusCode != 200) {
      throw HelpApiException(
        response.statusCode,
        response.body.isNotEmpty ? response.body : 'Erreur réseau',
      );
    }
    final json = jsonDecode(response.body) as Map<String, dynamic>;
    return HelpCategoryListResponse.fromJson(json);
  }

  Future<HelpArticleListResponse> getArticles({
    required String collectionSlug,
    required String categorySlug,
    String locale = 'fr',
  }) async {
    final uri = Uri.parse(
      Config.helpCategoryArticlesUrl(collectionSlug, categorySlug),
    ).replace(queryParameters: {'locale': locale});
    final response = await _getWithRetry(uri);
    if (response.statusCode != 200) {
      throw HelpApiException(
        response.statusCode,
        response.body.isNotEmpty ? response.body : 'Erreur réseau',
      );
    }
    final json = jsonDecode(response.body) as Map<String, dynamic>;
    return HelpArticleListResponse.fromJson(json);
  }

  /// Récupère un article Help par son slug (premier trouvé parmi les articles publiés).
  Future<HelpArticleDetail?> getArticleBySlug(String slug, {String locale = 'fr'}) async {
    final uri = Uri.parse(Config.helpArticleBySlugUrl).replace(
      queryParameters: {'slug': slug, 'locale': locale},
    );
    final response = await _getWithRetry(uri);
    if (response.statusCode == 404) return null;
    if (response.statusCode != 200) {
      throw HelpApiException(
        response.statusCode,
        response.body.isNotEmpty ? response.body : 'Erreur réseau',
      );
    }
    final json = jsonDecode(response.body) as Map<String, dynamic>;
    final article = json['article'] as Map<String, dynamic>?;
    if (article == null) return null;
    return HelpArticleDetail.fromJson(article);
  }

  Future<HelpArticleDetail> getArticleDetail({
    required String collectionSlug,
    required String categorySlug,
    required String articleSlug,
    String locale = 'fr',
  }) async {
    final uri = Uri.parse(
      Config.helpArticleDetailUrl(collectionSlug, categorySlug, articleSlug),
    ).replace(queryParameters: {'locale': locale});
    final response = await _getWithRetry(uri);
    if (response.statusCode != 200) {
      throw HelpApiException(
        response.statusCode,
        response.body.isNotEmpty ? response.body : 'Erreur réseau',
      );
    }
    final json = jsonDecode(response.body) as Map<String, dynamic>;
    return HelpArticleDetail.fromJson((json['article'] as Map<String, dynamic>? ?? const {}));
  }

  Future<List<HelpTaggedArticleItem>> getArticlesByTag({
    required String tagType,
    required String tagId,
    String locale = 'fr',
  }) async {
    final uri = Uri.parse(Config.helpArticlesByTagUrl).replace(
      queryParameters: {
        'type': tagType,
        'id': tagId,
        'locale': locale,
      },
    );
    final response = await _getWithRetry(uri);
    if (response.statusCode != 200) {
      throw HelpApiException(
        response.statusCode,
        response.body.isNotEmpty ? response.body : 'Erreur réseau',
      );
    }
    final json = jsonDecode(response.body) as Map<String, dynamic>;
    final list = (json['articles'] as List<dynamic>? ?? const []);
    return list
        .whereType<Map<String, dynamic>>()
        .map(HelpTaggedArticleItem.fromJson)
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
