/// États UX explicites pour le routage d’entrée (hors spinners internes).
enum AppEntryUxState {
  /// Aucun jeton local ou session serveur non valide après contrôle.
  loggedOut,

  /// JWT OK mais PIN local pas encore défini.
  serverAuthenticatedButLocalSecurityNotSetup,

  /// JWT OK + PIN configuré — passage par Secure Gate / biométrie.
  serverAuthenticatedAndLocalSecurityReady,

  /// Déverrouillage local en cours (PIN / Face ID) — pas une destination de routeur.
  unlockingLocalAccess,
}
