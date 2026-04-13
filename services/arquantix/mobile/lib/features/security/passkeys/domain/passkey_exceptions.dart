/// Passkeys indisponibles sur cette plateforme / build (pas de plugin natif ou refus utilisateur).
class PasskeyUnavailableException implements Exception {
  PasskeyUnavailableException([this.message = 'Passkeys unavailable']);
  final String message;
  @override
  String toString() => 'PasskeyUnavailableException: $message';
}

/// L’utilisateur a fermé / annulé le dialogue système passkey.
class PasskeyUserCancelledException implements Exception {
  PasskeyUserCancelledException([this.message = 'Passkey cancelled']);
  final String message;
  @override
  String toString() => message;
}

/// Échec authenticator (hors annulation) — UX : fallback OTP.
class PasskeyAuthenticatorFailureException implements Exception {
  PasskeyAuthenticatorFailureException(this.message);
  final String message;
  @override
  String toString() => message;
}

/// Réponse API passkey inattendue.
class PasskeyApiException implements Exception {
  PasskeyApiException(this.statusCode, this.body);
  final int statusCode;
  final String body;
  @override
  String toString() => 'PasskeyApiException($statusCode): $body';
}
