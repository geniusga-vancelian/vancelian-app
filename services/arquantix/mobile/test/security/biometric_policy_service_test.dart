import 'package:arquantix_news/features/security/local_access/biometric_policy_service.dart';
import 'package:arquantix_news/features/security/local_access/local_relock_engine.dart';
import 'package:arquantix_news/features/security/local_access/session_security_snapshot.dart';
import 'package:arquantix_news/features/security/passcode/domain/secure_access_config.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  final t0 = DateTime(2026, 4, 3, 12, 0, 0);

  test('step-up JWT seul => ne force pas le PIN avant biométrie auto (unlock local)', () async {
    final force = await BiometricPolicyService.instance.shouldForcePinInsteadOfBiometric(
      biometricRecentFailCount: 0,
      lastBiometricFailAt: null,
      now: t0,
    );
    expect(force, isFalse);
  });

  test('échecs biométriques récents => forcer le PIN', () async {
    final force = await BiometricPolicyService.instance.shouldForcePinInsteadOfBiometric(
      biometricRecentFailCount: SecureAccessConfig.biometricFailuresBeforePinFirst,
      lastBiometricFailAt: t0.subtract(const Duration(seconds: 30)),
      now: t0,
    );
    expect(force, isTrue);
  });

  test(
    'shouldRelockNow: resume court => false',
    () async {
      final need = await BiometricPolicyService.instance.shouldRelockNow(
        lastActiveAt: t0.subtract(const Duration(seconds: 20)),
        riskContext: const SessionSecuritySnapshot(),
        appLifecycleContext: const AppLifecycleSecurityContext(
          isReturningFromBackground: true,
        ),
        now: t0,
      );
      expect(need, isFalse);
    },
    skip: 'SessionIntelligenceManager lit le stockage sécurisé (pas de plugin en test unitaire).',
  );

  test(
    'shouldRelockNow: resume long => true',
    () async {
      final need = await BiometricPolicyService.instance.shouldRelockNow(
        lastActiveAt: t0.subtract(const Duration(seconds: 60)),
        riskContext: const SessionSecuritySnapshot(),
        appLifecycleContext: const AppLifecycleSecurityContext(
          isReturningFromBackground: true,
        ),
        now: t0,
      );
      expect(need, isTrue);
    },
    skip: 'SessionIntelligenceManager lit le stockage sécurisé (pas de plugin en test unitaire).',
  );

  test(
    'shouldRelockNow: pas de double décision si pas de retour background',
    () async {
      final need = await BiometricPolicyService.instance.shouldRelockNow(
        lastActiveAt: t0.subtract(const Duration(minutes: 30)),
        riskContext: const SessionSecuritySnapshot(),
        appLifecycleContext: const AppLifecycleSecurityContext(
          isReturningFromBackground: false,
          backgroundDuration: Duration(minutes: 30),
        ),
        now: t0,
      );
      expect(need, isFalse);
    },
    skip: 'SessionIntelligenceManager lit le stockage sécurisé (pas de plugin en test unitaire).',
  );
}
