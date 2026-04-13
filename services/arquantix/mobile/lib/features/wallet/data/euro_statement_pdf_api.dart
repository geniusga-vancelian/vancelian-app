import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

import '../../../core/config.dart';
import '../../../core/session_bearer_http.dart';

class EuroStatementPdfApi {
  Future<Uint8List> fetchStatementPdf() async {
    final uri = Uri.parse(Config.euroAccountStatementPdfUrl);
    final response = await http.get(
      uri,
      headers: await SessionBearerHttp.downloadHeadersAppScoped(
        uri: uri,
        debugTag: 'EuroStatementPdfApi.fetchStatementPdf',
      ),
    );

    if (response.statusCode == 200) {
      return response.bodyBytes;
    }

    var message = 'Impossible de générer le relevé pour le moment.';
    try {
      final decoded = jsonDecode(response.body);
      if (decoded is Map<String, dynamic>) {
        final detail = decoded['detail'];
        if (detail is String && detail.trim().isNotEmpty) {
          message = detail;
        } else if (detail is List && detail.isNotEmpty) {
          final first = detail.first;
          if (first is Map && first['msg'] is String) {
            message = first['msg'] as String;
          }
        }
      }
    } catch (_) {
      if (response.body.isNotEmpty && response.body.length < 500) {
        message = response.body;
      }
    }

    throw EuroStatementPdfException(response.statusCode, message);
  }
}

class EuroStatementPdfException implements Exception {
  EuroStatementPdfException(this.statusCode, this.message);

  final int statusCode;
  final String message;

  @override
  String toString() => 'EuroStatementPdfException($statusCode): $message';
}
