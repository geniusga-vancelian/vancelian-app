import 'dart:convert';
import 'package:http/http.dart' as http;

import '../../../core/config.dart';
import '../../../core/session_bearer_http.dart';
import '../domain/models/cash_data.dart';

class CashApiException implements Exception {
  final String message;
  final int? statusCode;
  CashApiException(this.message, {this.statusCode});

  @override
  String toString() => 'CashApiException($statusCode): $message';
}

class CashApi {
  final String? baseUrl;
  const CashApi({this.baseUrl});

  Future<CashData> fetchCashData() async {
    final url = Uri.parse(baseUrl ?? Config.cashUrl);
    final headers = await SessionBearerHttp.jsonHeadersAppScoped(
      uri: url,
      debugTag: 'CashApi.fetchCashData',
    );
    final response = await http.get(url, headers: headers);

    if (response.statusCode == 404) {
      throw CashApiException(
        'Aucun compte cash pour ce profil, ou session absente.',
        statusCode: 404,
      );
    }

    if (response.statusCode != 200) {
      throw CashApiException(
        'Failed to fetch cash data',
        statusCode: response.statusCode,
      );
    }

    final json = jsonDecode(response.body) as Map<String, dynamic>;
    return CashData.fromJson(json);
  }
}
