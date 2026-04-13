import '../local_access/local_relock_engine.dart';
import '../local_access/session_security_snapshot.dart';
import '../passcode/data/session_service.dart';

/// Couche « Session Intelligence » côté client : lecture JWT persistée + relock / biométrie / re-auth.
class SessionIntelligenceManager {
  SessionIntelligenceManager._();

  static final SessionService _session = SessionService.instance;

  /// Snapshot combinant stockage sécurisé (claims mis à jour au login / refresh).
  static Future<SessionSecuritySnapshot> currentSnapshot() async =>
      _session.readSecuritySnapshot();

  /// Seuil de relock effectif (relock JWT / session trust LOW → plus strict).
  static Future<Duration> effectiveRelockThreshold({
    required RelockEngineConfig config,
    DateTime? now,
  }) async {
    final snap = await currentSnapshot();
    return relockThresholdForSnapshot(
      snapshot: snap,
      config: config,
      now: now ?? DateTime.now(),
    );
  }

  static Duration relockThresholdForSnapshot({
    required SessionSecuritySnapshot snapshot,
    required RelockEngineConfig config,
    required DateTime now,
  }) {
    if (snapshot.jwtRelockRequired) {
      return config.relockThresholdHighRisk;
    }
    final st = snapshot.sessionTrustLevel?.toUpperCase().trim();
    if (st == 'LOW' || snapshot.stepUpOtpRequired) {
      return config.relockThresholdHighRisk;
    }
    if (st == 'HIGH' &&
        !snapshot.stepUpOtpRequired &&
        !snapshot.jwtRelockRequired) {
      return config.relockThresholdNormal + config.maxGracePeriod;
    }
    return LocalRelockEngine.effectiveThreshold(
      snapshot: snapshot,
      now: now,
      config: config,
    );
  }

  static Future<bool> shouldRelockNow({
    required AppLifecycleSecurityContext appLifecycleContext,
    required RelockEngineConfig config,
    DateTime? now,
  }) async {
    final snap = await currentSnapshot();
    final n = now ?? DateTime.now();
    final threshold = relockThresholdForSnapshot(
      snapshot: snap,
      config: config,
      now: n,
    );
    if (!appLifecycleContext.isReturningFromBackground) return false;
    final bg = appLifecycleContext.backgroundDuration;
    if (bg == null) return false;
    final lastUnlock = snap.lastLocalUnlockAt;
    if (lastUnlock != null) {
      final sinceUnlock = n.difference(lastUnlock);
      if (sinceUnlock < config.debounceAfterLocalUnlock) {
        return false;
      }
    }
    return bg >= threshold;
  }

  static Future<bool> shouldRequireBiometric() async {
    final snap = await currentSnapshot();
    return snap.jwtBiometricHint || snap.stepUpOtpRequired;
  }

  /// Indique qu’il faut renvoyer l’utilisateur vers un login complet (claim / politique future).
  static Future<bool> shouldForceReauth() async {
    final t = await _session.readAccessToken();
    if (t == null || t.isEmpty) return true;
    final snap = SessionSecuritySnapshot.fromAccessTokenClaims(t);
    return snap.stepUpOtpRequired && snap.jwtRelockRequired;
  }
}
