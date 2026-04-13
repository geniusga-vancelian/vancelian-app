/// Clés stockées uniquement via [FlutterSecureStorage] (Keychain / Keystore).
abstract final class PasscodeStorageKeys {
  static const String deviceSaltB64 = 'arqx.sec.device_salt_b64';
  static const String passcodeHashB64 = 'arqx.sec.passcode_hash_b64';
  static const String failedAttempts = 'arqx.sec.failed_attempts';
  static const String lockUntilMs = 'arqx.sec.lock_until_ms';
  static const String lockoutTier = 'arqx.sec.lockout_tier';
  static const String lockoutEvents = 'arqx.sec.lockout_events';
  static const String biometricEnabled = 'arqx.sec.biometric_enabled';

  /// Valeurs : [BiometricOnboardingPromptState.storageValue] (remplace l’ancien booléen « handled »).
  static const String biometricOnboardingPromptState =
      'arqx.sec.biometric_onboarding_prompt_state';

  /// Ancien booléen « handled » (migration lecture seule).
  static const String biometricOnboardingHandledLegacy =
      'arqx.sec.biometric_onboarding_handled';

  /// Valeurs : [PushNotificationOnboardingPromptState.storageValue].
  static const String pushOnboardingPromptState =
      'arqx.sec.push_onboarding_prompt_state';

  /// Préférence locale « toutes les notifications » (`1` / `0`).
  static const String pushNotificationsPreferenceEnabled =
      'arqx.sec.push_notifications_pref_enabled';

  /// Dernier affichage d’un prompt onboarding push **automatique** (ms epoch UTC).
  static const String lastPushOnboardingPromptAtMs =
      'arqx.sec.last_push_onboarding_prompt_at_ms';

  /// Prénom d’accueil (legacy, hors `sub`) — migré vers clé par utilisateur si besoin.
  static const String clientGreetingFirstNameLegacy =
      'arqx.sec.client_greeting_first_name';
}

abstract final class SessionStorageKeys {
  static const String accessToken = 'arqx.sess.access_token';
  static const String refreshToken = 'arqx.sess.refresh_token';
  static const String accessExpiresAtMs = 'arqx.sess.access_expires_at_ms';
  /// Prénom affiché sur l’écran code (non secret ; JWT ou renseigné à la connexion).
  static const String clientGreetingFirstName = 'arqx.sess.greeting_first_name';
  /// Device API (`X-Device-ID`) — UUID v4 persistant (Keychain / Keystore), **stable reboot / cold start**.
  static const String deviceId = 'arqx.sess.device_id';
  /// UUID d’installation stable (Phase 3.1 — fingerprint, non secret).
  static const String installId = 'arqx.sess.install_id';

  /// PR D2 — octets privés ECDSA P-256 (base64) pour signatures refresh (`X-Device-Signature`).
  static const String deviceSigningEcdsaSecretB64 = 'arqx.sess.device_signing_ecdsa_sk_b64';

  /// Dernier e-mail utilisé pour une connexion réussie (UX « bon retour »).
  static const String loginLastEmail = 'arqx.sess.login_last_email';

  /// Dernier mobile saisi (E.164) sur l’écran login — pour cohérence du parcours.
  static const String loginLastPhoneE164 = 'arqx.sess.login_last_phone_e164';

  /// JSON des claims sécurité issus du dernier JWT (step-up, confiance, auth_str).
  static const String securityClaimsJson = 'arqx.sess.security_claims_json';

  /// Horodatage client : dernière action sensible (optionnel).
  static const String lastSensitiveActionAtMs = 'arqx.sess.last_sensitive_action_ms';

  /// Dernier déverrouillage local réussi (PIN ou biométrie).
  static const String lastLocalUnlockAtMs = 'arqx.sess.last_local_unlock_ms';

  /// Échecs biométriques récents (compteur, reset au succès).
  static const String biometricRecentFailCount = 'arqx.sess.bio_fail_count';

  /// Dernier échec biométrique (ms depuis epoch).
  static const String lastBiometricFailAtMs = 'arqx.sess.bio_fail_at_ms';

  /// Après inscription mobile : ouvrir le flux EU registration une fois le PIN créé.
  static const String pendingEuRegistrationAfterPasscode =
      'arqx.sess.pending_eu_reg_after_passcode';
}
