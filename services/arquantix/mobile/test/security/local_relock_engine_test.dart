import 'package:arquantix_news/features/security/local_access/local_relock_engine.dart';
import 'package:arquantix_news/features/security/local_access/session_security_snapshot.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  const config = RelockEngineConfig(
    relockThresholdNormal: Duration(seconds: 45),
    relockThresholdHighRisk: Duration(seconds: 15),
    maxGracePeriod: Duration(minutes: 3),
    debounceAfterLocalUnlock: Duration(seconds: 4),
  );

  final t0 = DateTime(2026, 4, 3, 12, 0, 0);

  test('resume court => pas de relock (sous seuil normal)', () {
    expect(
      LocalRelockEngine.shouldRelockNow(
        appLifecycleContext: const AppLifecycleSecurityContext(
          isReturningFromBackground: true,
          backgroundDuration: Duration(seconds: 30),
        ),
        riskContext: const SessionSecuritySnapshot(),
        now: t0,
        config: config,
      ),
      isFalse,
    );
  });

  test('resume long => relock (au-delà du seuil normal)', () {
    expect(
      LocalRelockEngine.shouldRelockNow(
        appLifecycleContext: const AppLifecycleSecurityContext(
          isReturningFromBackground: true,
          backgroundDuration: Duration(seconds: 50),
        ),
        riskContext: const SessionSecuritySnapshot(),
        now: t0,
        config: config,
      ),
      isTrue,
    );
  });

  test('risque élevé => relock plus agressif (seuil court)', () {
    expect(
      LocalRelockEngine.shouldRelockNow(
        appLifecycleContext: const AppLifecycleSecurityContext(
          isReturningFromBackground: true,
          backgroundDuration: Duration(seconds: 20),
        ),
        riskContext: const SessionSecuritySnapshot(stepUpOtpRequired: true),
        now: t0,
        config: config,
      ),
      isTrue,
    );
  });

  test('pas de relock si pas de retour background', () {
    expect(
      LocalRelockEngine.shouldRelockNow(
        appLifecycleContext: const AppLifecycleSecurityContext(
          isReturningFromBackground: false,
          backgroundDuration: Duration(minutes: 10),
        ),
        riskContext: const SessionSecuritySnapshot(),
        now: t0,
        config: config,
      ),
      isFalse,
    );
  });

  test('debounce après unlock local => pas de double relock', () {
    expect(
      LocalRelockEngine.shouldRelockNow(
        appLifecycleContext: const AppLifecycleSecurityContext(
          isReturningFromBackground: true,
          backgroundDuration: Duration(minutes: 5),
        ),
        riskContext: SessionSecuritySnapshot(
          lastLocalUnlockAt: t0.subtract(const Duration(seconds: 2)),
        ),
        now: t0,
        config: config,
      ),
      isFalse,
    );
  });

  test('auth serveur forte => seuil effectif plus long (grâce)', () {
    final threshold = LocalRelockEngine.effectiveThreshold(
      snapshot: const SessionSecuritySnapshot(lastAuthStrength: 'passkey'),
      now: t0,
      config: config,
    );
    expect(threshold, greaterThan(const Duration(seconds: 45)));
  });
}
