import 'dart:convert';
import 'dart:developer' as developer;
import 'dart:typed_data';

import 'package:http/http.dart' as http;

import '../../../core/config.dart';
import '../../../core/session_bearer_http.dart';

/// Extrait un message d’erreur lisible depuis une réponse JSON (FastAPI, Next BFF, etc.).
String? parseOperationStatementErrorBody(String body) {
  if (body.trim().isEmpty) return null;
  try {
    final decoded = jsonDecode(body);
    if (decoded is Map<String, dynamic>) {
      final detail = decoded['detail'];
      if (detail is String && detail.trim().isNotEmpty) {
        return detail.trim();
      }
      if (detail is List && detail.isNotEmpty) {
        final first = detail.first;
        if (first is Map && first['msg'] is String) {
          return (first['msg'] as String).trim();
        }
      }
      // Next.js BFF / autres proxies : souvent `message` ou `error` sans `detail`
      final m = decoded['message'];
      if (m is String && m.trim().isNotEmpty) {
        return m.trim();
      }
      final err = decoded['error'];
      if (err is String && err.trim().isNotEmpty) {
        return err.trim();
      }
    }
  } catch (_) {
    /* corps non JSON */
  }
  return null;
}

void _logPdf(String message) {
  developer.log(message, name: 'OPERATION_STATEMENT_PDF');
}

/// PDF relevé d’une seule opération (proxy BFF → API Python).
class TransactionOperationPdfApi {
  Future<Uint8List> fetchOperationStatementPdf(String transactionId) async {
    final uri = Uri.parse(
      Config.transactionOperationStatementPdfUrl(transactionId),
    );
    _logPdf('fetch start url=$uri transactionId=$transactionId');

    final response = await http.get(
      uri,
      headers: await SessionBearerHttp.downloadHeadersAppScoped(
        uri: uri,
        debugTag: 'TransactionOperationPdfApi.fetchOperationStatementPdf',
      ),
    );

    final ct = response.headers['content-type'] ?? '';
    _logPdf(
      'response status=${response.statusCode} contentType=$ct bytes=${response.bodyBytes.length}',
    );

    if (response.statusCode == 200) {
      if (!ct.toLowerCase().contains('pdf') &&
          response.bodyBytes.isNotEmpty &&
          response.bodyBytes.length < 4000) {
        try {
          final n = response.bodyBytes.length < 200 ? response.bodyBytes.length : 200;
          final head = utf8.decode(response.bodyBytes.sublist(0, n));
          if (head.trimLeft().startsWith('{')) {
            _logPdf(
              'warning: status 200 but body looks like JSON not PDF — possible proxy misconfiguration',
            );
          }
        } catch (_) {}
      }
      return response.bodyBytes;
    }

    var message = 'Impossible de générer le relevé pour le moment.';
    final parsed = parseOperationStatementErrorBody(response.body);
    if (parsed != null && parsed.isNotEmpty) {
      message = parsed;
    } else if (response.body.isNotEmpty && response.body.length < 800) {
      message = response.body;
    }

    final excerpt = response.body.length > 400
        ? '${response.body.substring(0, 400)}…'
        : response.body;
    _logPdf('error HTTP ${response.statusCode} parsedMessage=$message excerpt=$excerpt');

    throw TransactionOperationPdfException(response.statusCode, message);
  }
}

class TransactionOperationPdfException implements Exception {
  TransactionOperationPdfException(this.statusCode, this.message);

  final int statusCode;
  final String message;

  @override
  String toString() => 'TransactionOperationPdfException($statusCode): $message';
}
