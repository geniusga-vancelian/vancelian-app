import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../core/config.dart';
import '../../../core/session_bearer_http.dart';

class LandingPageBuilderApiException implements Exception {
  LandingPageBuilderApiException(this.statusCode, this.message);

  final int statusCode;
  final String message;

  @override
  String toString() => 'LandingPageBuilderApiException($statusCode): $message';
}

class LandingPagePayload {
  const LandingPagePayload({
    required this.slug,
    required this.title,
    required this.description,
    required this.config,
  });

  final String slug;
  final String? title;
  final String? description;
  final Map<String, dynamic> config;
}

class LandingPageBuilderApi {
  LandingPageBuilderApi({String? baseUrl}) : baseUrl = baseUrl ?? Config.apiBaseUrl;

  final String baseUrl;

  Future<Map<String, String>> _headers(Uri uri, String tag) =>
      SessionBearerHttp.jsonHeadersAppScoped(uri: uri, debugTag: tag);

  Future<LandingPagePayload> fetchBySlug(
    String slug, {
    bool draft = true,
    String locale = 'fr',
    bool forceRefresh = false,
  }) async {
    final uriBase = Uri.parse(
      '${Config.flutterLandingPageUrl(slug)}?status=${draft ? 'draft' : 'published'}&locale=$locale',
    );
    final uri = forceRefresh
        ? uriBase.replace(
            queryParameters: {
              ...uriBase.queryParameters,
              '_t': DateTime.now().millisecondsSinceEpoch.toString(),
            },
          )
        : uriBase;

    final response = await http.get(
      uri,
      headers: await _headers(uri, 'LandingPageBuilderApi.fetchBySlug'),
    );
    if (response.statusCode != 200) {
      throw LandingPageBuilderApiException(
        response.statusCode,
        response.body.isNotEmpty ? response.body : 'Erreur reseau',
      );
    }

    final json = jsonDecode(response.body) as Map<String, dynamic>;
    final page = json['page'];
    final landing = json['landing'];
    if (page is! Map<String, dynamic> || landing is! Map<String, dynamic>) {
      throw LandingPageBuilderApiException(500, 'Payload landing invalide');
    }

    return LandingPagePayload(
      slug: (page['slug'] ?? '').toString(),
      title: page['title']?.toString(),
      description: page['description']?.toString(),
      config: landing,
    );
  }
}
