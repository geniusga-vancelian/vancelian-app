import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../core/config.dart';
import '../../../core/session_bearer_http.dart';
import '../domain/models/euro_account_data.dart';

class EuroAccountApi {
  Future<EuroAccountData> fetchEuroAccount() async {
    final uri = Uri.parse(Config.euroAccountUrl);
    final response = await http.get(
      uri,
      headers: await SessionBearerHttp.jsonHeadersAppScoped(
        uri: uri,
        debugTag: 'EuroAccountApi.fetchEuroAccount',
      ),
    );

    if (response.statusCode == 404) {
      throw EuroAccountNotFoundException();
    }

    if (response.statusCode != 200) {
      throw EuroAccountApiException(
        response.statusCode,
        response.body.isNotEmpty ? response.body : 'Erreur réseau',
      );
    }

    final json = jsonDecode(response.body) as Map<String, dynamic>;
    return EuroAccountData.fromJson(json);
  }
}

class EuroAccountNotFoundException implements Exception {
  @override
  String toString() => 'Aucun compte Euro trouvé';
}

class EuroAccountApiException implements Exception {
  EuroAccountApiException(this.statusCode, this.message);

  final int statusCode;
  final String message;

  @override
  String toString() => 'EuroAccountApiException($statusCode): $message';
}
