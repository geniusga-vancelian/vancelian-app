import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../core/config.dart';
import '../../../core/http_error_display.dart';
import '../../../core/locale_preference.dart';
import '../../../core/session_bearer_http.dart';
import '../domain/models/article.dart';
import '../domain/models/article_detail.dart';

class BlogApiException implements Exception {
  BlogApiException(this.statusCode, String rawBody)
      : rawBody = rawBody,
        message = userFacingHttpErrorMessage(statusCode, rawBody);

  final int statusCode;
  /// Corps brut renvoyé par le serveur (debug / logs).
  final String rawBody;
  /// Message dérivé (JSON API, err.message Next.js, etc.), tronqué pour l’UI.
  final String message;

  @override
  String toString() => 'BlogApiException($statusCode): $message';
}

class BlogApi {
  final String baseUrl;

  BlogApi({String? baseUrl}) : baseUrl = baseUrl ?? Config.apiBaseUrl;

  Future<Map<String, String>> _appScopedHeaders(Uri uri, String tag) =>
      SessionBearerHttp.jsonHeadersAppScoped(uri: uri, debugTag: tag);

  /// Récupère le feed blog (featured, highlighted, articles, categories)
  Future<BlogFeedResponse> getFeed({
    String? locale,
    String? category,
    String? articleType,
    /// API : `market` | `company` | `analysis`
    String? segment,
    String? projectId,
    int page = 1,
    int pageSize = 10,
  }) async {
    final effectiveLocale = LocalePreference.instance.resolve(locale);
    final uri = Uri.parse(Config.blogFeedUrl).replace(
      queryParameters: {
        'locale': effectiveLocale,
        if (category != null) 'category': category,
        if (articleType != null && articleType.isNotEmpty)
          'articleType': articleType,
        if (segment != null && segment.isNotEmpty) 'segment': segment,
        if (projectId != null && projectId.isNotEmpty) 'projectId': projectId,
        'page': page.toString(),
        'pageSize': pageSize.toString(),
      },
    );

    final response = await http.get(uri);

    if (response.statusCode != 200) {
      throw BlogApiException(
        response.statusCode,
        response.body.isNotEmpty ? response.body : 'Erreur réseau',
      );
    }

    final json = jsonDecode(response.body) as Map<String, dynamic>;
    return BlogFeedResponse.fromJson(json);
  }

  /// Récupère les articles liés à un projet via la section « related project » (table article_projects).
  /// Endpoint : GET /api/projects/[id]/articles. Pas de filtrage par catégorie.
  Future<List<ArticlePreview>> getProjectArticles(
    String projectId, {
    String? locale,
    int limit = 20,
  }) async {
    final effectiveLocale = LocalePreference.instance.resolve(locale);
    final uri = Uri.parse(Config.projectArticlesUrl(projectId)).replace(
      queryParameters: {
        'locale': effectiveLocale,
        'limit': limit.toString(),
      },
    );

    final response = await http.get(
      uri,
      headers: await _appScopedHeaders(uri, 'BlogApi.getProjectArticles'),
    );

    if (response.statusCode != 200) {
      throw BlogApiException(
        response.statusCode,
        response.body.isNotEmpty ? response.body : 'Erreur réseau',
      );
    }

    final json = jsonDecode(response.body) as Map<String, dynamic>;
    final list = json['articles'] as List<dynamic>?;
    if (list == null) return [];

    return list
        .map((e) => ArticlePreview.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// Récupère un article par son slug
  Future<ArticleDetail?> getArticle(String slug, {String? locale}) async {
    final effectiveLocale = LocalePreference.instance.resolve(locale);
    final uri = Uri.parse(Config.blogArticleUrl(slug)).replace(
      queryParameters: {'locale': effectiveLocale},
    );

    final response = await http.get(uri);

    if (response.statusCode == 404) {
      return null;
    }

    if (response.statusCode != 200) {
      throw BlogApiException(
        response.statusCode,
        response.body.isNotEmpty ? response.body : 'Erreur réseau',
      );
    }

    final json = jsonDecode(response.body) as Map<String, dynamic>;
    return ArticleDetail.fromJson(json);
  }
}

/// Réponse du feed blog
class BlogFeedResponse {
  final ArticlePreview? featured;
  final List<ArticlePreview> highlighted;
  final List<ArticlePreview> companyNews;
  final List<ArticlePreview> articles;
  /// Catégories « offres » (investment)
  final List<BlogCategory> categories;
  /// Tags blog / ArticleCategory (prioritaires pour filtres si présents côté UI)
  final List<BlogCategory> articleCategories;
  final BlogPagination pagination;

  const BlogFeedResponse({
    this.featured,
    required this.highlighted,
    this.companyNews = const [],
    required this.articles,
    required this.categories,
    this.articleCategories = const [],
    required this.pagination,
  });

  factory BlogFeedResponse.fromJson(Map<String, dynamic> json) {
    ArticlePreview? featured;
    if (json['featured'] != null) {
      featured = ArticlePreview.fromJson(json['featured'] as Map<String, dynamic>);
    }

    return BlogFeedResponse(
      featured: featured,
      highlighted: (json['highlighted'] as List<dynamic>?)
              ?.map((e) => ArticlePreview.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      companyNews: (json['companyNews'] as List<dynamic>?)
              ?.map((e) => ArticlePreview.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      articles: (json['articles'] as List<dynamic>?)
              ?.map((e) => ArticlePreview.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      categories: (json['categories'] as List<dynamic>?)
              ?.map((e) => BlogCategory.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      articleCategories: (json['articleCategories'] as List<dynamic>?)
              ?.map((e) => BlogCategory.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      pagination: BlogPagination.fromJson(
        json['pagination'] as Map<String, dynamic>? ?? {},
      ),
    );
  }
}

class BlogCategory {
  final String id;
  final String slug;
  final String label;

  const BlogCategory({required this.id, required this.slug, required this.label});

  factory BlogCategory.fromJson(Map<String, dynamic> json) {
    return BlogCategory(
      id: json['id'] as String,
      slug: json['slug'] as String,
      label: json['label'] as String,
    );
  }
}

class BlogPagination {
  final int page;
  final int pageSize;
  final int total;
  final bool hasMore;

  const BlogPagination({
    required this.page,
    required this.pageSize,
    required this.total,
    required this.hasMore,
  });

  factory BlogPagination.fromJson(Map<String, dynamic> json) {
    return BlogPagination(
      page: (json['page'] as num?)?.toInt() ?? 1,
      pageSize: (json['pageSize'] as num?)?.toInt() ?? 10,
      total: (json['total'] as num?)?.toInt() ?? 0,
      hasMore: json['hasMore'] as bool? ?? false,
    );
  }
}
