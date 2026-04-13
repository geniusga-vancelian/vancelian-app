import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../core/config.dart';
import '../../../core/http_error_display.dart';
import '../../../core/session_bearer_http.dart';

class DashboardLayoutApiException implements Exception {
  final int statusCode;
  final String message;

  DashboardLayoutApiException(this.statusCode, this.message);

  @override
  String toString() => 'DashboardLayoutApiException($statusCode): $message';
}

/// API de lecture du layout dashboard en base (via endpoint public web).
class DashboardLayoutApi {
  final String baseUrl;

  DashboardLayoutApi({String? baseUrl}) : baseUrl = baseUrl ?? Config.apiBaseUrl;

  Future<Map<String, dynamic>> getDashboardLayout({bool forceRefresh = false}) async {
    final baseUri = Uri.parse(Config.dashboardLayoutUrl);
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
        debugTag: 'DashboardLayoutApi.getDashboardLayout',
      ),
    );

    if (response.statusCode != 200) {
      final raw = response.body.isNotEmpty ? response.body : 'Erreur réseau';
      throw DashboardLayoutApiException(
        response.statusCode,
        userFacingHttpErrorMessage(response.statusCode, raw),
      );
    }

    final json = jsonDecode(response.body) as Map<String, dynamic>;
    final layout = json['layout'];
    if (layout is! Map<String, dynamic>) {
      throw DashboardLayoutApiException(500, 'Payload layout invalide');
    }

    return layout;
  }
}
