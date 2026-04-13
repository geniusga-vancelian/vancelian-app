import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../core/config.dart';
import '../../../core/session_bearer_http.dart';

class TransactionDetailLayoutApiException implements Exception {
  final int statusCode;
  final String message;

  TransactionDetailLayoutApiException(this.statusCode, this.message);

  @override
  String toString() => 'TransactionDetailLayoutApiException($statusCode): $message';
}

/// API de lecture du layout transaction detail en base (via endpoint public web).
class TransactionDetailLayoutApi {
  final String baseUrl;

  TransactionDetailLayoutApi({String? baseUrl}) : baseUrl = baseUrl ?? Config.apiBaseUrl;

  Future<Map<String, dynamic>> getTransactionDetailLayout({
    bool forceRefresh = false,
  }) async {
    final baseUri = Uri.parse(Config.transactionDetailLayoutUrl);
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
        debugTag: 'TransactionDetailLayoutApi.getTransactionDetailLayout',
      ),
    );

    if (response.statusCode != 200) {
      throw TransactionDetailLayoutApiException(
        response.statusCode,
        response.body.isNotEmpty ? response.body : 'Erreur reseau',
      );
    }

    final json = jsonDecode(response.body) as Map<String, dynamic>;
    final layout = json['layout'];
    if (layout is! Map<String, dynamic>) {
      throw TransactionDetailLayoutApiException(500, 'Payload layout invalide');
    }

    return layout;
  }
}
