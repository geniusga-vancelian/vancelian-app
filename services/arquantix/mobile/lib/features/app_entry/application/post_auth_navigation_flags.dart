/// Drapeaux de navigation **one-shot** (même processus) après auth / bootstrap.
class PostAuthNavigationFlags {
  PostAuthNavigationFlags._();

  /// Après fin d’inscription → [MainShellScreen] : ne pas afficher le re-prompt push
  /// (le skip registration doit être honoré jusqu’au **prochain** retour session).
  static bool suppressNextMainShellPushReloginPrompt = false;
}
