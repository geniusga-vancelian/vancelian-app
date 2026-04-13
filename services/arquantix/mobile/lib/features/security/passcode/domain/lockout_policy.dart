/// Politique anti brute-force (côté client — complément serveur requis en prod).
class LockoutPolicy {
  LockoutPolicy._();

  static const int maxAttemptsBeforeLock = 5;

  /// Vagues de verrouillage successives : 30s → 5min → 1h (puis 1h).
  static Duration lockDurationForTier(int tier) {
    switch (tier.clamp(0, 99)) {
      case 0:
        return const Duration(seconds: 30);
      case 1:
        return const Duration(minutes: 5);
      default:
        return const Duration(hours: 1);
    }
  }

  /// Après ce nombre d’épisodes de verrouillage, on purge session locale (+ PIN).
  static const int lockoutEventsBeforeHardReset = 4;
}
