import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../core/config.dart';
import '../../../core/session_bearer_http.dart';

class OffersLayoutApiException implements Exception {
  final int statusCode;
  final String message;

  OffersLayoutApiException(this.statusCode, this.message);

  @override
  String toString() => 'OffersLayoutApiException($statusCode): $message';
}

/// API de lecture du layout Offers en base (via endpoint public web).
class OffersLayoutApi {
  final String baseUrl;

  OffersLayoutApi({String? baseUrl}) : baseUrl = baseUrl ?? Config.apiBaseUrl;

  Future<Map<String, String>> _headers(Uri uri, String tag) =>
      SessionBearerHttp.jsonHeadersAppScoped(uri: uri, debugTag: tag);

  Future<Map<String, dynamic>> getOffersLayout({bool forceRefresh = false}) async {
    final baseUri = Uri.parse(Config.offersLayoutUrl);
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
      headers: await _headers(uri, 'OffersLayoutApi.getOffersLayout'),
    );
    if (response.statusCode != 200) {
      throw OffersLayoutApiException(
        response.statusCode,
        response.body.isNotEmpty ? response.body : 'Erreur réseau',
      );
    }

    final json = jsonDecode(response.body) as Map<String, dynamic>;
    final layout = json['layout'];
    if (layout is! Map<String, dynamic>) {
      throw OffersLayoutApiException(500, 'Payload layout invalide');
    }
    return layout;
  }
}
