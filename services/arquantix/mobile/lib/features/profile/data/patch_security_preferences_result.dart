import 'dart:convert';

/// Résultat PATCH `/profile/security-preferences` (V1 structuré).
sealed class PatchSecurityPreferencesResult {
  const PatchSecurityPreferencesResult();

  bool get isSuccess => this is PatchSecurityPreferencesSuccess;
}

final class PatchSecurityPreferencesSuccess extends PatchSecurityPreferencesResult {
  const PatchSecurityPreferencesSuccess();
}

enum PatchSecurityPreferencesFailureKind {
  /// 422 — payload invalide (ex. biométrie incohérente).
  validation422,

  /// 401 / 403
  unauthorized,

  /// Timeout, pas de réseau, 5xx.
  network,

  /// Route ou ressource introuvable (ex. 404).
  endpointNotFound,

  /// Jeton d’accès absent ou en-têtes Bearer impossibles (client).
  sessionMissing,

  /// Autre 4xx / corps illisible.
  clientError,
}

final class PatchSecurityPreferencesFailure extends PatchSecurityPreferencesResult {
  const PatchSecurityPreferencesFailure(this.kind, {this.detail});

  final PatchSecurityPreferencesFailureKind kind;
  final String? detail;
}

/// Interprète une réponse HTTP PATCH (hors exceptions socket / timeout).
PatchSecurityPreferencesResult patchSecurityPreferencesResultFromHttp({
  required int statusCode,
  required String body,
}) {
  if (statusCode == 200) {
    return const PatchSecurityPreferencesSuccess();
  }
  if (statusCode == 401 || statusCode == 403) {
    return const PatchSecurityPreferencesFailure(
      PatchSecurityPreferencesFailureKind.unauthorized,
    );
  }
  if (statusCode == 404) {
    return const PatchSecurityPreferencesFailure(
      PatchSecurityPreferencesFailureKind.endpointNotFound,
      detail: 'http_404',
    );
  }
  if (statusCode == 422) {
    String? detail;
    try {
      final decoded = jsonDecode(body);
      if (decoded is Map<String, dynamic>) {
        detail = decoded['detail']?.toString();
      }
    } catch (_) {
      detail = body;
    }
    return PatchSecurityPreferencesFailure(
      PatchSecurityPreferencesFailureKind.validation422,
      detail: detail,
    );
  }
  if (statusCode >= 500 || statusCode == 408) {
    return PatchSecurityPreferencesFailure(
      PatchSecurityPreferencesFailureKind.network,
      detail: statusCode.toString(),
    );
  }
  return PatchSecurityPreferencesFailure(
    PatchSecurityPreferencesFailureKind.clientError,
    detail: 'http_$statusCode',
  );
}
