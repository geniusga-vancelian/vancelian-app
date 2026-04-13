/// États explicites du cycle de vie session (app mobile).
///
/// Une seule source de vérité « applicative » — le stockage reste dans [SessionService],
/// l’identité dérivée dans [SessionIdentityContext].
enum SessionLifecycleState {
  /// Aucun jeton d’accès stocké (ou effacé).
  anonymous,

  /// Flux login / OTP en cours (UI).
  authenticating,

  /// Jetons serveur présents, contrôle local (PIN / secure gate) non validé pour cette « session UI ».
  authenticatedLocked,

  /// Jeton lisible + identité synchronisable ; appels API autorisés (sous réserve réseau).
  authenticatedReady,

  /// Home : bootstrap + chargements dashboard en cours.
  bootstrappingHome,

  /// Refresh access JWT en cours ([SessionService.refreshAccessToken]).
  refreshingToken,

  /// Session serveur considérée invalide (ex. refresh 401, JWT refusé).
  expired,

  /// Déconnexion en cours (révocation / effacement).
  loggingOut,

  /// Trop de tentatives PIN / reset sécurité — retour login attendu.
  hardResetRequired,

  /// Erreur auth récupérable (affichage / retry).
  authError,
}

/// Événements qui font évoluer la machine (intention explicite).
enum SessionLifecycleEvent {
  /// L’utilisateur ouvre le flux login (OTP, etc.).
  loginFlowStarted,

  /// Jetons persistés après succès serveur ([SessionService.storeTokens]).
  accessTokenPersisted,

  /// Déverrouillage passcode / biométrie OK avant [MainShellScreen].
  passcodeUnlocked,

  /// Début chargement Home (bootstrap + parallèle).
  homeBootstrapStarted,

  /// Fin chargement Home (succès ou abandon contrôlé).
  homeBootstrapCompleted,

  /// Début refresh JWT (futur branchement refresh).
  refreshStarted,

  /// Refresh réussi.
  refreshSucceeded,

  /// Refresh rejeté (401) → transition vers [expired] puis nettoyage.
  refreshFailed,

  /// Refresh sans nouveau jeton (réseau / 5xx) — session locale conservée.
  refreshAborted,

  /// Utilisateur ou code déclenche une déconnexion.
  logoutStarted,

  /// Effacement local / révocation terminé ([SessionService.clearSession] ou équivalent).
  tokensCleared,

  /// Reset sécurité (trop de tentatives PIN, etc.).
  hardResetSecurity,

  /// Cold start : jetons présents (reprise session).
  coldStartTokensPresent,
}
