import 'dart:developer' as developer;

/// Logs structurés pour le débogage des flux auth (sans backend).
void logAuthHttpFailure({
  required String operation,
  Uri? uri,
  String? method,
  int? statusCode,
  String? responseBody,
  String? requestPayload,
  Object? error,
  StackTrace? stackTrace,
}) {
  final parts = <String>['auth_http', operation];
  if (method != null) parts.add(method);
  if (uri != null) parts.add(uri.toString());
  if (statusCode != null) parts.add('status=$statusCode');
  if (requestPayload != null && requestPayload.isNotEmpty) {
    parts.add('payload=${_truncate(requestPayload, 500)}');
  }
  developer.log(
    parts.join(' '),
    name: 'AuthHttp',
    error: error,
    stackTrace: stackTrace,
  );
  if (responseBody != null && responseBody.isNotEmpty) {
    developer.log(
      'auth_http response body: ${_truncate(responseBody, 1200)}',
      name: 'AuthHttp',
    );
  }
}

String _truncate(String s, int max) {
  if (s.length <= max) return s;
  return '${s.substring(0, max)}…';
}
