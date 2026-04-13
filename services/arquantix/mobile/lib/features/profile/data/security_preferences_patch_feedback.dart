import 'patch_security_preferences_result.dart';

/// Route ``/profile/security-preferences`` absente (souvent dev) ou 404 : le client
/// planifie déjà un retry — pas besoin de snackbar alarmiste sur le dashboard.
bool suppressSecurityPreferencesFailureSnackBar(
  PatchSecurityPreferencesFailure failure,
) {
  if (failure.kind == PatchSecurityPreferencesFailureKind.endpointNotFound) {
    return true;
  }
  if (failure.kind == PatchSecurityPreferencesFailureKind.clientError &&
      failure.detail == 'http_404') {
    return true;
  }
  return false;
}

/// Messages utilisateur pour les échecs PATCH préférences (biométrie / push).
String userMessageForPatchSecurityPreferencesFailure(
  PatchSecurityPreferencesFailure failure,
) {
  final kind = failure.kind;
  final detail = failure.detail;
  switch (kind) {
    case PatchSecurityPreferencesFailureKind.validation422:
      return detail ??
          'Le serveur a refusé ces données. Si le problème persiste, contactez le support.';
    case PatchSecurityPreferencesFailureKind.unauthorized:
      return 'Session expirée. Reconnectez-vous pour synchroniser vos préférences.';
    case PatchSecurityPreferencesFailureKind.network:
      return 'Problème réseau ou serveur temporairement indisponible. Nouvel essai automatique sous peu.';
    case PatchSecurityPreferencesFailureKind.endpointNotFound:
      return 'Service de préférences introuvable sur cet environnement. Vérifiez la configuration ou réessayez après mise à jour.';
    case PatchSecurityPreferencesFailureKind.sessionMissing:
      return 'Session indisponible pour synchroniser. Réessayez après connexion ; une nouvelle tentative sera lancée automatiquement.';
    case PatchSecurityPreferencesFailureKind.clientError:
      if (detail == 'http_404') {
        return 'Service de préférences introuvable sur cet environnement. Vérifiez la configuration ou réessayez après mise à jour.';
      }
      return 'Synchronisation impossible pour le moment. Nouvel essai automatique sous peu.';
  }
}
