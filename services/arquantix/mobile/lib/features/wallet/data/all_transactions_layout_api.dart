import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../core/config.dart';
import '../../../core/session_bearer_http.dart';

class AllTransactionsLayoutApiException implements Exception {
  final int statusCode;
  final String message;

  AllTransactionsLayoutApiException(this.statusCode, this.message);

  @override
  String toString() => 'AllTransactionsLayoutApiException($statusCode): $message';
}

/// API de lecture du layout all-transactions en base (via endpoint public web).
class AllTransactionsLayoutApi {
  final String baseUrl;

  AllTransactionsLayoutApi({String? baseUrl}) : baseUrl = baseUrl ?? Config.apiBaseUrl;

  Future<Map<String, dynamic>> getAllTransactionsLayout({
    bool forceRefresh = false,
  }) async {
    final baseUri = Uri.parse(Config.allTransactionsLayoutUrl);
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
      headers: await SessionBearerHttp.jsonHeadersAppScoped(
        uri: uri,
        debugTag: 'AllTransactionsLayoutApi.getAllTransactionsLayout',
      ),
    );

    if (response.statusCode != 200) {
      throw AllTransactionsLayoutApiException(
        response.statusCode,
        response.body.isNotEmpty ? response.body : 'Erreur reseau',
      );
    }

    final json = jsonDecode(response.body) as Map<String, dynamic>;
    final layout = json['layout'];
    if (layout is! Map<String, dynamic>) {
      throw AllTransactionsLayoutApiException(500, 'Payload layout invalide');
    }

    return layout;
  }
}
