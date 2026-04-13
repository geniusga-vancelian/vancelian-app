/// Politique unifiée pour les **flux sensibles après authentification** (PIN, OTP, passkeys,
/// actions sensibles). Objectif : une seule grille de lecture pour audits et code.
///
/// **Continuité sûre (même exécution)** : l’utilisateur vient de s’authentifier, les jetons
/// sont cohérents, pas de redémarrage app → enchaînements comme setup PIN → Secure Gate
/// restent autorisés via [PostLoginLocalSecurityFlow] et routes dédiées.
///
/// **Après interruption** (cold start, kill, crash, parfois changement de compte) : les flux
/// qui **installent** une barrière de sécurité ou **prouvent** un facteur ne doivent **pas**
/// reprendre depuis un état partiel persistant sans réévaluation explicite.

/// Nature du flux (audit / documentation).
enum PostAuthSensitiveFlowKind {
  /// Première création du PIN après login — **jamais** repris au cold start sans re-login.
  passcodeSetupFirstTime,

  /// Déverrouillage local (PIN / biométrie) — au cold start, **nouveau** passage par l’écran
  /// prévu (Secure Gate), pas une reprise d’un wizard interrompu.
  passcodeUnlock,

  /// Vérification OTP SMS pendant login ou step-up.
  otpVerifySms,

  /// Vérification OTP e-mail (admin ou login).
  otpVerifyEmail,

  /// Assertion WebAuthn / passkey (login).
  passkeyAssertion,

  /// Enregistrement passkey — ne pas reprendre un enrôlement à moitié après kill.
  passkeyEnrollment,

  /// Parcours « code oublié » / reset local — repartir d’une entrée sûre.
  forgotPasscodeFlow,

  /// Confirmation explicite d’action sensible (virement, etc.).
  sensitiveActionConfirmation,

  /// Portail avant shell quand PIN déjà configuré.
  secureGate,

  /// Activation biométrie après PIN — traité comme setup sensible.
  localBiometricEnrollment,
}

/// Qualification centralisée : que faire **après cold start / relance app** ?
enum PostAuthFlowColdStartPolicy {
  /// Ne jamais rouvrir l’étape depuis un état persistant ; exiger re-login + 2FA / flux complet.
  forbiddenWithoutFullReauth,

  /// Le cold start ne « reprend » pas un wizard ; l’utilisateur repasse par la **porte**
  /// prévue (ex. Secure Gate / unlock), pas par un écran de setup interrompu.
  reenterThroughSecureGateOrLogin,

  /// Pas d’état sensible persistant attendu (documentation seulement).
  notApplicable,
}

/// Tags pour corrélation code ↔ doc (éviter règles ad hoc dispersées).
enum PostAuthFlowTag {
  sensitiveTransientFlow,
  localSecurityFlow,
  resumableSameExecutionOnly,
  resumableAfterColdStart,
  forbiddenToResumeAfterColdStart,
}

/// Règles pures — utilisées par les tests et la doc ; le routage réel reste dans les écrans.
class PostAuthSensitiveFlowPolicy {
  PostAuthSensitiveFlowPolicy._();

  /// Après **cold start** : politique documentée pour chaque type de flux.
  static PostAuthFlowColdStartPolicy coldStartPolicy(PostAuthSensitiveFlowKind kind) {
    switch (kind) {
      case PostAuthSensitiveFlowKind.passcodeSetupFirstTime:
      case PostAuthSensitiveFlowKind.otpVerifySms:
      case PostAuthSensitiveFlowKind.otpVerifyEmail:
      case PostAuthSensitiveFlowKind.passkeyAssertion:
      case PostAuthSensitiveFlowKind.passkeyEnrollment:
      case PostAuthSensitiveFlowKind.forgotPasscodeFlow:
      case PostAuthSensitiveFlowKind.sensitiveActionConfirmation:
      case PostAuthSensitiveFlowKind.localBiometricEnrollment:
        return PostAuthFlowColdStartPolicy.forbiddenWithoutFullReauth;
      case PostAuthSensitiveFlowKind.passcodeUnlock:
      case PostAuthSensitiveFlowKind.secureGate:
        return PostAuthFlowColdStartPolicy.reenterThroughSecureGateOrLogin;
    }
  }

  /// Tags descriptifs pour un flux (plusieurs peuvent s’appliquer).
  static Set<PostAuthFlowTag> tagsFor(PostAuthSensitiveFlowKind kind) {
    switch (kind) {
      case PostAuthSensitiveFlowKind.passcodeSetupFirstTime:
        return {
          PostAuthFlowTag.sensitiveTransientFlow,
          PostAuthFlowTag.localSecurityFlow,
          PostAuthFlowTag.resumableSameExecutionOnly,
          PostAuthFlowTag.forbiddenToResumeAfterColdStart,
        };
      case PostAuthSensitiveFlowKind.passcodeUnlock:
      case PostAuthSensitiveFlowKind.secureGate:
        return {
          PostAuthFlowTag.localSecurityFlow,
          PostAuthFlowTag.resumableAfterColdStart,
          PostAuthFlowTag.forbiddenToResumeAfterColdStart,
        };
      case PostAuthSensitiveFlowKind.otpVerifySms:
      case PostAuthSensitiveFlowKind.otpVerifyEmail:
      case PostAuthSensitiveFlowKind.passkeyAssertion:
        return {
          PostAuthFlowTag.sensitiveTransientFlow,
          PostAuthFlowTag.resumableSameExecutionOnly,
          PostAuthFlowTag.forbiddenToResumeAfterColdStart,
        };
      case PostAuthSensitiveFlowKind.passkeyEnrollment:
      case PostAuthSensitiveFlowKind.localBiometricEnrollment:
        return {
          PostAuthFlowTag.sensitiveTransientFlow,
          PostAuthFlowTag.localSecurityFlow,
          PostAuthFlowTag.resumableSameExecutionOnly,
          PostAuthFlowTag.forbiddenToResumeAfterColdStart,
        };
      case PostAuthSensitiveFlowKind.forgotPasscodeFlow:
      case PostAuthSensitiveFlowKind.sensitiveActionConfirmation:
        return {
          PostAuthFlowTag.sensitiveTransientFlow,
          PostAuthFlowTag.forbiddenToResumeAfterColdStart,
        };
    }
  }
}
