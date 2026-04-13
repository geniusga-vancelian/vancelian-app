import 'session_security_snapshot.dart';

/// Paramètres du moteur de relock (réutilisables en tests).
class RelockEngineConfig {
  const RelockEngineConfig({
    required this.relockThresholdNormal,
    required this.relockThresholdHighRisk,
    required this.maxGracePeriod,
    required this.debounceAfterLocalUnlock,
  });

  /// Seuil standard : au-delà du temps en arrière-plan → relock.
  final Duration relockThresholdNormal;

  /// Seuil agressif (session à risque).
  final Duration relockThresholdHighRisk;

  /// Bonus maximal ajouté au seuil si auth serveur forte / action sensible récente.
  final Duration maxGracePeriod;

  /// Après un unlock local, ignorer un resume trop rapproché (évite doubles prompts).
  final Duration debounceAfterLocalUnlock;
}

/// Contexte cycle de vie minimal (sans dépendre de Flutter).
class AppLifecycleSecurityContext {
  const AppLifecycleSecurityContext({
    required this.isReturningFromBackground,
    this.backgroundDuration,
  });

  final bool isReturningFromBackground;

  /// Durée passée en arrière-plan depuis le dernier `paused` ; null si inconnue.
  final Duration? backgroundDuration;
}

/// Moteur pur : décide si un relock local est nécessaire au resume.
class LocalRelockEngine {
  LocalRelockEngine._();

  /// Seuil effectif selon le snapshot (risque + grâce).
  static Duration effectiveThreshold({
    required SessionSecuritySnapshot snapshot,
    required DateTime now,
    required RelockEngineConfig config,
  }) {
    final base = snapshot.isElevatedLocalRisk
        ? config.relockThresholdHighRisk
        : config.relockThresholdNormal;

    // Pas de « grâce » allongeant le seuil si le contexte local est déjà à risque.
    if (snapshot.isElevatedLocalRisk) return base;

    var grace = Duration.zero;
    final auth = snapshot.lastAuthStrength?.toLowerCase().trim();
    const strongAuth = {'passkey', 'webauthn', 'otp', 'mfa'};
    if (auth != null && strongAuth.contains(auth)) {
      grace = config.maxGracePeriod;
    }
    final sens = snapshot.lastSensitiveActionAt;
    if (sens != null && now.difference(sens) <= config.maxGracePeriod) {
      final g = config.maxGracePeriod ~/ 2;
      grace = grace >= g ? grace : g;
    }
    return base + grace;
  }

  /// `true` = ouvrir l’écran de déverrouillage local.
  static bool shouldRelockNow({
    required AppLifecycleSecurityContext appLifecycleContext,
    required SessionSecuritySnapshot riskContext,
    required DateTime now,
    required RelockEngineConfig config,
    /// Seuil imposé par [SessionIntelligenceManager] (JWT / strust) si non null.
    Duration? effectiveThresholdOverride,
  }) {
    if (!appLifecycleContext.isReturningFromBackground) return false;
    final bg = appLifecycleContext.backgroundDuration;
    if (bg == null) return false;

    final lastUnlock = riskContext.lastLocalUnlockAt;
    if (lastUnlock != null) {
      final sinceUnlock = now.difference(lastUnlock);
      if (sinceUnlock < config.debounceAfterLocalUnlock) {
        return false;
      }
    }

    final threshold = effectiveThresholdOverride ??
        effectiveThreshold(
          snapshot: riskContext,
          now: now,
          config: config,
        );
    return bg >= threshold;
  }
}
