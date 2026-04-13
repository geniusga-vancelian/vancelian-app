import 'dart:convert';
import 'package:http/http.dart' as http;

import '../../../core/config.dart';
import '../../../core/session_bearer_http.dart';
import '../domain/models/placement_position.dart';

class PlacementsApiException implements Exception {
  final String message;
  final int? statusCode;
  PlacementsApiException(this.message, {this.statusCode});

  @override
  String toString() => 'PlacementsApiException($statusCode): $message';
}

class PlacementsApi {
  const PlacementsApi();

  Future<Map<String, String>> _headers(Uri url, String tag) =>
      SessionBearerHttp.jsonHeadersAppScoped(
        uri: url,
        debugTag: tag,
      );

  Future<PlacementsData> fetchEarnPositions() async {
    final url = Uri.parse(Config.lendingEarnPositionsUrl);
    final response = await http.get(
      url,
      headers: await _headers(url, 'PlacementsApi.fetchEarnPositions'),
    );

    if (response.statusCode == 404) {
      throw PlacementsApiException(
        'Session ou profil client introuvable (connexion / inscription requise).',
        statusCode: 404,
      );
    }

    if (response.statusCode != 200) {
      throw PlacementsApiException(
        'Failed to fetch earn positions',
        statusCode: response.statusCode,
      );
    }

    final json = jsonDecode(response.body) as Map<String, dynamic>;
    return PlacementsData.fromJson(json);
  }

  Future<Map<String, dynamic>> fetchLendingDashboard() async {
    final url = Uri.parse(Config.lendingDashboardUrl);
    final response = await http.get(
      url,
      headers: await _headers(url, 'PlacementsApi.fetchLendingDashboard'),
    );

    if (response.statusCode != 200) {
      throw PlacementsApiException(
        'Failed to fetch lending dashboard',
        statusCode: response.statusCode,
      );
    }

    return jsonDecode(response.body) as Map<String, dynamic>;
  }
}
