import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../domain/biometric_onboarding_prompt_state.dart';
import '../domain/push_notification_onboarding_prompt_state.dart';
import '../domain/lockout_policy.dart';
import '../domain/passcode_storage_keys.dart';
import '../domain/passcode_user_keys.dart';
import 'passcode_crypto.dart';
import 'session_service.dart';

/// Gestion locale du PIN 6 chiffres + lockout (aucune donnée envoyée au backend).
///
/// Le passcode est stocké **par utilisateur** (claim JWT `sub`) lorsque le token est un JWT.
/// Sinon, repli sur les clés **legacy** globales (un seul PIN pour l’appareil).
/// La déconnexion standard **ne supprime pas** le passcode (voir [AuthLogout]).
class PasscodeService {
  PasscodeService._();
  static final PasscodeService instance = PasscodeService._();

  static const int pinLength = 6;

  final FlutterSecureStorage _storage = const FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
    iOptions: IOSOptions(
      accessibility: KeychainAccessibility.first_unlock_this_device,
    ),
  );

  bool _initialized = false;
  bool? _configuredCache;
  String? _bindingSub;

  PasscodeUserKeys get _keys => PasscodeUserKeys.forBinding(_bindingSub);

  Future<String?> _bindingIdFromSession() async {
    final token = await SessionService.instance.readAccessToken();
    if (token == null || token.isEmpty) return null;
    return SessionService.extractJwtSubject(token);
  }

  /// Recharge le binding (`sub` du JWT courant) et l’état « PIN configuré ».
  Future<void> init() async {
    final sub = await _bindingIdFromSession();
    _bindingSub = sub;
    _initialized = true;
    await _refreshConfiguredCache();
  }

  Future<void> _refreshConfiguredCache() async {
    final keys = _keys;
    var h = await _storage.read(key: keys.passcodeHashB64);
    if ((h == null || h.isEmpty) && _bindingSub != null) {
      await _migrateLegacyToBoundUser(keys);
      h = await _storage.read(key: keys.passcodeHashB64);
    }
    _configuredCache = h != null && h.isNotEmpty;
  }

  /// Copie unique legacy → utilisateur courant (mise à jour app avec PIN déjà créé).
  Future<void> _migrateLegacyToBoundUser(PasscodeUserKeys keys) async {
    final legacyHash =
        await _storage.read(key: PasscodeStorageKeys.passcodeHashB64);
    if (legacyHash == null || legacyHash.isEmpty) return;
    final legacySalt =
        await _storage.read(key: PasscodeStorageKeys.deviceSaltB64);
    await _storage.write(key: keys.passcodeHashB64, value: legacyHash);
    if (legacySalt != null && legacySalt.isNotEmpty) {
      await _storage.write(key: keys.deviceSaltB64, value: legacySalt);
    }
    final bio =
        await _storage.read(key: PasscodeStorageKeys.biometricEnabled);
    if (bio != null && bio.isNotEmpty) {
      await _storage.write(key: keys.biometricEnabled, value: bio);
    }
    final bioOnboardingLegacy = await _storage.read(
      key: PasscodeStorageKeys.biometricOnboardingHandledLegacy,
    );
    if (bioOnboardingLegacy != null && bioOnboardingLegacy.isNotEmpty) {
      await _storage.write(
        key: keys.biometricOnboardingHandledLegacy,
        value: bioOnboardingLegacy,
      );
    }
    final bioPrompt = await _storage.read(
      key: PasscodeStorageKeys.biometricOnboardingPromptState,
    );
    if (bioPrompt != null && bioPrompt.isNotEmpty) {
      await _storage.write(
        key: keys.biometricOnboardingPromptState,
        value: bioPrompt,
      );
    }
    final pushPrompt = await _storage.read(
      key: PasscodeStorageKeys.pushOnboardingPromptState,
    );
    if (pushPrompt != null && pushPrompt.isNotEmpty) {
      await _storage.write(
        key: keys.pushOnboardingPromptState,
        value: pushPrompt,
      );
    }
    final pushPref = await _storage.read(
      key: PasscodeStorageKeys.pushNotificationsPreferenceEnabled,
    );
    if (pushPref != null && pushPref.isNotEmpty) {
      await _storage.write(
        key: keys.pushNotificationsPreferenceEnabled,
        value: pushPref,
      );
    }
    final lastPushMs = await _storage.read(
      key: PasscodeStorageKeys.lastPushOnboardingPromptAtMs,
    );
    if (lastPushMs != null && lastPushMs.isNotEmpty) {
      await _storage.write(
        key: keys.lastPushOnboardingPromptAtMs,
        value: lastPushMs,
      );
    }
    for (final k in [
      PasscodeStorageKeys.failedAttempts,
      PasscodeStorageKeys.lockUntilMs,
      PasscodeStorageKeys.lockoutTier,
      PasscodeStorageKeys.lockoutEvents,
    ]) {
      final v = await _storage.read(key: k);
      if (v != null) {
        final target = switch (k) {
          PasscodeStorageKeys.failedAttempts => keys.failedAttempts,
          PasscodeStorageKeys.lockUntilMs => keys.lockUntilMs,
          PasscodeStorageKeys.lockoutTier => keys.lockoutTier,
          PasscodeStorageKeys.lockoutEvents => keys.lockoutEvents,
          _ => k,
        };
        await _storage.write(key: target, value: v);
      }
    }
    await _storage.delete(key: PasscodeStorageKeys.passcodeHashB64);
    await _storage.delete(key: PasscodeStorageKeys.deviceSaltB64);
    await _storage.delete(key: PasscodeStorageKeys.biometricEnabled);
    await _storage.delete(key: PasscodeStorageKeys.biometricOnboardingHandledLegacy);
    await _storage.delete(key: PasscodeStorageKeys.biometricOnboardingPromptState);
    await _storage.delete(key: PasscodeStorageKeys.pushOnboardingPromptState);
    await _storage.delete(key: PasscodeStorageKeys.pushNotificationsPreferenceEnabled);
    await _storage.delete(key: PasscodeStorageKeys.lastPushOnboardingPromptAtMs);
    await _storage.delete(key: PasscodeStorageKeys.failedAttempts);
    await _storage.delete(key: PasscodeStorageKeys.lockUntilMs);
    await _storage.delete(key: PasscodeStorageKeys.lockoutTier);
    await _storage.delete(key: PasscodeStorageKeys.lockoutEvents);
  }

  bool get isPasscodeConfigured {
    assert(_initialized, 'Call PasscodeService.instance.init() first');
    return _configuredCache == true;
  }

  Future<bool> isBiometricUnlockEnabled() async {
    final v = await _storage.read(key: _keys.biometricEnabled);
    return v == '1';
  }

  Future<void> setBiometricUnlockEnabled(bool enabled) async {
    await _storage.write(
      key: _keys.biometricEnabled,
      value: enabled ? '1' : '0',
    );
  }

  /// État produit onboarding biométrie (voir [BiometricOnboardingPromptState]).
  ///
  /// Migre l’ancien booléen `…_handled` (`1`/`0`) vers l’enum au premier accès.
  ///
  /// **Aucune valeur persistée** pour ce binding (nouvel appareil, réinstall, premier passage) :
  /// retourne [BiometricOnboardingPromptState.neverSeen] — le gate onboarding suit alors le backend.
  Future<BiometricOnboardingPromptState> getBiometricOnboardingPromptState() async {
    if (!_initialized) await init();
    final keys = _keys;
    final rawNew = await _storage.read(key: keys.biometricOnboardingPromptState);
    final parsed = BiometricOnboardingPromptState.tryParse(rawNew);
    if (parsed != null) {
      return parsed;
    }
    final rawOld = await _storage.read(key: keys.biometricOnboardingHandledLegacy);
    if (rawOld == '1') {
      final bioOn = await isBiometricUnlockEnabled();
      final migrated = bioOn
          ? BiometricOnboardingPromptState.enabled
          : BiometricOnboardingPromptState.skipped;
      await _storage.write(
        key: keys.biometricOnboardingPromptState,
        value: migrated.storageValue,
      );
      await _storage.delete(key: keys.biometricOnboardingHandledLegacy);
      return migrated;
    }
    if (rawOld == '0') {
      await _storage.delete(key: keys.biometricOnboardingHandledLegacy);
    }
    return BiometricOnboardingPromptState.neverSeen;
  }

  /// Si l’état stocké est [BiometricOnboardingPromptState.unavailable] mais le capteur est
  /// à nouveau utilisable, repasse à [neverSeen] (persisté). Appeler au chargement PIN et au resume.
  Future<void> syncBiometricOnboardingPromptStateWithDeviceCapability(
    bool deviceSupportsBiometric,
  ) async {
    if (!_initialized) await init();
    final current = await getBiometricOnboardingPromptState();
    final next = reconcileBiometricOnboardingPromptStateForDevice(
      stored: current,
      deviceSupportsBiometric: deviceSupportsBiometric,
    );
    if (next != current) {
      await setBiometricOnboardingPromptState(next);
    }
  }

  Future<void> setBiometricOnboardingPromptState(
    BiometricOnboardingPromptState state,
  ) async {
    await _storage.write(
      key: _keys.biometricOnboardingPromptState,
      value: state.storageValue,
    );
    await _storage.delete(key: _keys.biometricOnboardingHandledLegacy);
  }

  /// Onboarding notifications (voir [PushNotificationOnboardingPromptState]).
  Future<PushNotificationOnboardingPromptState>
      getPushOnboardingPromptState() async {
    if (!_initialized) await init();
    final raw = await _storage.read(key: _keys.pushOnboardingPromptState);
    final parsed = PushNotificationOnboardingPromptState.tryParse(raw);
    return parsed ?? PushNotificationOnboardingPromptState.neverSeen;
  }

  Future<void> setPushOnboardingPromptState(
    PushNotificationOnboardingPromptState state,
  ) async {
    if (!_initialized) await init();
    await _storage.write(
      key: _keys.pushOnboardingPromptState,
      value: state.storageValue,
    );
  }

  /// Préférence locale « toutes les notifications » (instantané UI, hors round-trip API).
  Future<bool> getPushNotificationsPreferenceEnabled() async {
    if (!_initialized) await init();
    final v = await _storage.read(key: _keys.pushNotificationsPreferenceEnabled);
    return v == '1';
  }

  Future<void> setPushNotificationsPreferenceEnabled(bool enabled) async {
    if (!_initialized) await init();
    await _storage.write(
      key: _keys.pushNotificationsPreferenceEnabled,
      value: enabled ? '1' : '0',
    );
  }

  /// Cooldown entre deux affichages **automatiques** du prompt push (écrans Profil exclus).
  static const Duration automaticPushOnboardingCooldown = Duration(hours: 24);

  /// Dernier instant où un prompt onboarding push automatique a été affiché (persisté).
  Future<DateTime?> getLastAutomaticPushOnboardingPromptAt() async {
    if (!_initialized) await init();
    final raw = await _storage.read(key: _keys.lastPushOnboardingPromptAtMs);
    final ms = int.tryParse(raw ?? '');
    if (ms == null) return null;
    return DateTime.fromMillisecondsSinceEpoch(ms, isUtc: true);
  }

  /// À appeler quand le modal onboarding push automatique est réellement affiché.
  Future<void> recordAutomaticPushOnboardingPromptDisplayed() async {
    if (!_initialized) await init();
    final ms = DateTime.now().toUtc().millisecondsSinceEpoch;
    await _storage.write(
      key: _keys.lastPushOnboardingPromptAtMs,
      value: '$ms',
    );
  }

  /// `true` si un nouvel affichage automatique serait **dans** la fenêtre 24h.
  static bool isWithinAutomaticPushOnboardingCooldown(
    DateTime? lastDisplayedAt,
    DateTime now,
  ) {
    if (lastDisplayedAt == null) return false;
    return now.difference(lastDisplayedAt) < automaticPushOnboardingCooldown;
  }

  Future<void> setPasscode(String pin) async {
    if (!_initialized) await init();
    if (!_isValidPin(pin)) {
      throw ArgumentError('PIN must be $pinLength digits');
    }
    final keys = _keys;
    var saltB64 = await _storage.read(key: keys.deviceSaltB64);
    if (saltB64 == null || saltB64.isEmpty) {
      final salt = PasscodeCrypto.generateSalt();
      saltB64 = base64Encode(salt);
      await _storage.write(
        key: keys.deviceSaltB64,
        value: saltB64,
      );
    }
    final saltBytes = base64Decode(saltB64);
    final hash = await PasscodeCrypto.hashPasscode(
      pin,
      Uint8List.fromList(saltBytes),
    );
    await _storage.write(
      key: keys.passcodeHashB64,
      value: hash,
    );
    await _resetLockoutState();
    _configuredCache = true;
  }

  Future<void> clearPasscodeAndLockState() async {
    final keys = _keys;
    await _storage.delete(key: keys.passcodeHashB64);
    await _storage.delete(key: keys.deviceSaltB64);
    await _resetLockoutState();
    await _storage.delete(key: keys.biometricEnabled);
    await _storage.delete(key: keys.biometricOnboardingPromptState);
    await _storage.delete(key: keys.biometricOnboardingHandledLegacy);
    await _storage.delete(key: keys.pushOnboardingPromptState);
    await _storage.delete(key: keys.pushNotificationsPreferenceEnabled);
    await _storage.delete(key: keys.lastPushOnboardingPromptAtMs);
    await _storage.delete(key: keys.lockoutEvents);
    _configuredCache = false;
  }

  Future<void> _resetLockoutState() async {
    final keys = _keys;
    await _storage.write(
      key: keys.failedAttempts,
      value: '0',
    );
    await _storage.delete(key: keys.lockUntilMs);
    await _storage.write(
      key: keys.lockoutTier,
      value: '0',
    );
  }

  Future<PasscodeVerifyResult> verifyPin(String pin) async {
    if (!_initialized) await init();
    if (!_isValidPin(pin)) {
      return PasscodeVerifyInvalidFormat();
    }
    final keys = _keys;
    final untilMs = int.tryParse(
      await _storage.read(key: keys.lockUntilMs) ?? '',
    );
    if (untilMs != null) {
      final until = DateTime.fromMillisecondsSinceEpoch(untilMs);
      if (DateTime.now().isBefore(until)) {
        return PasscodeVerifyLocked(until);
      }
      await _storage.delete(key: keys.lockUntilMs);
    }

    final saltB64 = await _storage.read(key: keys.deviceSaltB64);
    final storedHash = await _storage.read(key: keys.passcodeHashB64);
    if (saltB64 == null || storedHash == null) {
      return PasscodeVerifyNotConfigured();
    }

    final candidate = await PasscodeCrypto.hashPasscode(
      pin,
      Uint8List.fromList(base64Decode(saltB64)),
    );
    final ok = PasscodeCrypto.hashesEqualB64(candidate, storedHash);
    if (ok) {
      await _storage.write(
        key: keys.failedAttempts,
        value: '0',
      );
      await _storage.delete(key: keys.lockUntilMs);
      return PasscodeVerifySuccess();
    }

    final fails =
        (int.tryParse(
              await _storage.read(key: keys.failedAttempts) ?? '0',
            ) ??
            0) +
            1;
    await _storage.write(
      key: keys.failedAttempts,
      value: '$fails',
    );

    if (fails >= LockoutPolicy.maxAttemptsBeforeLock) {
      await _storage.write(
        key: keys.failedAttempts,
        value: '0',
      );
      final tier = int.tryParse(
            await _storage.read(key: keys.lockoutTier) ?? '0',
          ) ??
          0;
      final lock = LockoutPolicy.lockDurationForTier(tier);
      final until = DateTime.now().add(lock);
      await _storage.write(
        key: keys.lockUntilMs,
        value: '${until.millisecondsSinceEpoch}',
      );
      await _storage.write(
        key: keys.lockoutTier,
        value: '${tier + 1}',
      );
      final events = (int.tryParse(
                await _storage.read(key: keys.lockoutEvents) ?? '0',
              ) ??
              0) +
          1;
      await _storage.write(
        key: keys.lockoutEvents,
        value: '$events',
      );
      if (events >= LockoutPolicy.lockoutEventsBeforeHardReset) {
        if (kDebugMode) {
          debugPrint(
            '[PasscodeService] lockout threshold: clearing local secrets',
          );
        }
        await clearPasscodeAndLockState();
        return PasscodeVerifyHardReset();
      }
      return PasscodeVerifyLocked(until);
    }
    return PasscodeVerifyWrongPin();
  }

  Future<Duration?> remainingLockDuration() async {
    final keys = _keys;
    final untilMs = int.tryParse(
      await _storage.read(key: keys.lockUntilMs) ?? '',
    );
    if (untilMs == null) return null;
    final until = DateTime.fromMillisecondsSinceEpoch(untilMs);
    final d = until.difference(DateTime.now());
    if (d.isNegative) return null;
    return d;
  }

  static bool _isValidPin(String pin) {
    if (pin.length != pinLength) return false;
    return RegExp(r'^\d{6}$').hasMatch(pin);
  }
}

sealed class PasscodeVerifyResult {}

final class PasscodeVerifySuccess extends PasscodeVerifyResult {}

final class PasscodeVerifyWrongPin extends PasscodeVerifyResult {}

final class PasscodeVerifyInvalidFormat extends PasscodeVerifyResult {}

final class PasscodeVerifyNotConfigured extends PasscodeVerifyResult {}

final class PasscodeVerifyLocked extends PasscodeVerifyResult {
  PasscodeVerifyLocked(this.until);
  final DateTime until;
}

/// Session PIN effacée après trop de verrouillages — l’utilisateur doit se ré-authentifier (flux login / 2FA).
final class PasscodeVerifyHardReset extends PasscodeVerifyResult {}
