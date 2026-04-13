import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../core/config.dart';
import '../../../core/session_bearer_http.dart';

class OfferLayoutApiException implements Exception {
  final int statusCode;
  final String message;

  OfferLayoutApiException(this.statusCode, this.message);

  @override
  String toString() => 'OfferLayoutApiException($statusCode): $message';
}

/// API de lecture du layout page projet (offre exclusive) en base.
class OfferLayoutApi {
  final String baseUrl;

  OfferLayoutApi({String? baseUrl}) : baseUrl = baseUrl ?? Config.apiBaseUrl;

  Future<Map<String, String>> _headers(Uri uri, String tag) =>
      SessionBearerHttp.jsonHeadersAppScoped(uri: uri, debugTag: tag);

  Future<Map<String, dynamic>> getExclusiveOfferDetailLayout({
    bool forceRefresh = false,
  }) async {
    final baseUri = Uri.parse(Config.exclusiveOfferDetailLayoutUrl);
    final uri = forceRefresh
        ? baseUri.replace(
            queryParameters: {
              ...baseUri.queryParameters,
              '_t': DateTime.now().millisecondsSinceEpoch.toString(),
            },
          )
        : baseUri;
    final response = await http.get(
      uri,
      headers: await _headers(uri, 'OfferLayoutApi.getExclusiveOfferDetailLayout'),
    );

    if (response.statusCode != 200) {
      throw OfferLayoutApiException(
        response.statusCode,
        response.body.isNotEmpty ? response.body : 'Erreur reseau',
      );
    }

    final json = jsonDecode(response.body) as Map<String, dynamic>;
    final layout = json['layout'];
    if (layout is! Map<String, dynamic>) {
      throw OfferLayoutApiException(500, 'Payload layout invalide');
    }

    return layout;
  }
}
