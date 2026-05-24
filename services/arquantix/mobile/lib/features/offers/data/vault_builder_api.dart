import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../core/config.dart';
import '../../../core/locale_preference.dart';
import '../../../core/session_bearer_http.dart';
import '../../landing_preview/data/landing_page_builder_api.dart';

/// API pour récupérer un vault par slug (même interface que landing pour réutilisation du preview).
class VaultBuilderApi {
  VaultBuilderApi({String? baseUrl}) : baseUrl = baseUrl ?? Config.apiBaseUrl;

  final String baseUrl;

  Future<Map<String, String>> _headers(Uri uri, String tag) =>
      SessionBearerHttp.jsonHeadersAppScoped(uri: uri, debugTag: tag);

  Future<LandingPagePayload> fetchBySlug(
    String slug, {
    bool draft = false,
    String? locale,
    bool forceRefresh = false,
  }) async {
    final effectiveLocale = LocalePreference.instance.resolve(locale);
    final uriBase = Uri.parse(
      '${Config.vaultUrl(slug)}?status=${draft ? 'draft' : 'published'}&locale=$effectiveLocale',
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
      headers: await _headers(uri, 'VaultBuilderApi.fetchBySlug'),
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
      throw LandingPageBuilderApiException(500, 'Payload vault invalide');
    }

    return LandingPagePayload(
      slug: (page['slug'] ?? '').toString(),
      title: page['title']?.toString(),
      description: page['description']?.toString(),
      config: Map<String, dynamic>.from(vault),
    );
  }
}
