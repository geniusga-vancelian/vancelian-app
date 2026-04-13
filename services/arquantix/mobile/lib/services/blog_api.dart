import 'dart:convert';

import 'package:http/http.dart' as http;

import '../config.dart';
import '../core/http_error_display.dart';
import '../models/article.dart';
import '../models/article_detail.dart';

class BlogApiException implements Exception {
  BlogApiException(this.statusCode, String rawBody)
      : rawBody = rawBody,
        message = httpErrorBodyForDisplay(statusCode, rawBody);

  final int statusCode;
  final String rawBody;
  final String message;

  @override
  String toString() => 'BlogApiException($statusCode): $message';
}

class BlogApi {
  final String baseUrl;

  BlogApi({String? baseUrl}) : baseUrl = baseUrl ?? Config.apiBaseUrl;

  /// Récupère le feed blog (featured, highlighted, articles, categories)
  Future<BlogFeedResponse> getFeed({
    String locale = 'fr',
    String? category,
    int page = 1,
    int pageSize = 10,
  }) async {
    final uri = Uri.parse(Config.blogFeedUrl).replace(
      queryParameters: {
        'locale': locale,
        if (category != null) 'category': category,
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

  /// Récupère un article par son slug
  Future<ArticleDetail?> getArticle(String slug, {String locale = 'fr'}) async {
    final uri = Uri.parse(Config.blogArticleUrl(slug)).replace(
      queryParameters: {'locale': locale},
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
  final List<ArticlePreview> articles;
  final List<BlogCategory> categories;
  final BlogPagination pagination;

  const BlogFeedResponse({
    this.featured,
    required this.highlighted,
    required this.articles,
    required this.categories,
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
      articles: (json['articles'] as List<dynamic>?)
              ?.map((e) => ArticlePreview.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      categories: (json['categories'] as List<dynamic>?)
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
