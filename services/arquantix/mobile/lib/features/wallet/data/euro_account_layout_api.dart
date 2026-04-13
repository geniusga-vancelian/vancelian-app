import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../core/config.dart';
import '../../../core/session_bearer_http.dart';

class EuroAccountLayoutApiException implements Exception {
  final int statusCode;
  final String message;

  EuroAccountLayoutApiException(this.statusCode, this.message);

  @override
  String toString() => 'EuroAccountLayoutApiException($statusCode): $message';
}

class EuroAccountLayoutApi {
  final String baseUrl;

  EuroAccountLayoutApi({String? baseUrl}) : baseUrl = baseUrl ?? Config.apiBaseUrl;

  Future<Map<String, dynamic>> getEuroAccountLayout({bool forceRefresh = false}) async {
    final baseUri = Uri.parse(Config.euroAccountLayoutUrl);
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
        debugTag: 'EuroAccountLayoutApi.getEuroAccountLayout',
      ),
    );
    if (response.statusCode != 200) {
      throw EuroAccountLayoutApiException(
        response.statusCode,
        response.body.isNotEmpty ? response.body : 'Erreur réseau',
      );
    }

    final json = jsonDecode(response.body) as Map<String, dynamic>;
    final layout = json['layout'];
    if (layout is! Map<String, dynamic>) {
      throw EuroAccountLayoutApiException(500, 'Payload layout invalide');
    }
    return layout;
  }
}
