import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../../../../core/currency_preference.dart';
import '../../../../core/profile_leading_preference.dart';
import '../../../../core/secure_api_config.dart';
import '../../local_access/session_security_snapshot.dart';
import '../domain/jwt_access_claims.dart';
import '../domain/passcode_storage_keys.dart';
import '../domain/secure_access_config.dart';
import '../../../../core/post_auth_flow_security_events.dart';
import '../../../../core/session_identity_context.dart';
import '../../../../core/session/session_lifecycle_state.dart';
import '../../../../core/session/session_state_machine.dart';
import 'passcode_client_greeting_storage.dart';
import 'session_api.dart';

/// Jetons API — stockage secure uniquement. Aucun log de token.
class SessionService {
  SessionService._();
  static final SessionService instance = SessionService._();

  final FlutterSecureStorage _storage = const FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
    iOptions: IOSOptions(
      accessibility: KeychainAccessibility.first_unlock_this_device,
    ),
  );

  final SessionApi _api = SessionApi();

  /// Extrait un prénom depuis un JWT (claims + repli `sub` e-mail si besoin).
  static String? extractGreetingFirstNameFromAccessToken(String accessToken) =>
      jwtExtractGreetingFirstName(accessToken);

  /// Claim `sub` du JWT (identifiant stable du compte côté IdP / API).
  static String? extractJwtSubject(String accessToken) =>
      jwtExtractSubject(accessToken);

  Future<void> _deleteVolatileSessionSecurityKeys() async {
    await _storage.delete(key: SessionStorageKeys.securityClaimsJson);
    await _storage.delete(key: SessionStorageKeys.lastSensitiveActionAtMs);
    await _storage.delete(key: SessionStorageKeys.lastLocalUnlockAtMs);
    await _storage.delete(key: SessionStorageKeys.biometricRecentFailCount);
    await _storage.delete(key: SessionStorageKeys.lastBiometricFailAtMs);
  }

  Future<void> storeTokens({
    required String accessToken,
    String? refreshToken,
    DateTime? accessExpiresAt,
    String? greetingFirstName,
    /// Si `false`, pas d’événement [SessionLifecycleEvent.accessTokenPersisted] (ex. refresh JWT réussi).
    bool notifySessionLifecycle = true,
  }) async {
    final prevAccess = await _storage.read(key: SessionStorageKeys.accessToken);
    String? prevSub;
    if (prevAccess != null && prevAccess.isNotEmpty) {
      prevSub = extractJwtSubject(prevAccess);
    }
    final newSub = extractJwtSubject(accessToken);
    if (prevSub != null &&
        newSub != null &&
        prevSub.isNotEmpty &&
        newSub.isNotEmpty &&
        prevSub != newSub) {
      SessionIdentityContext.instance.clear();
      CurrencyPreference.instance.resetForLogout();
      ProfileLeadingPreference.instance.resetForLogout();
      await _deleteVolatileSessionSecurityKeys();
      await _deleteLoginRememberedIdentifiers();
      PostAuthFlowSecurityEvents.postAuthFlowInvalidatedOnUserSwitch(
        previousSubLength: prevSub.length,
        newSubLength: newSub.length,
      );
    }

    await _storage.write(
      key: SessionStorageKeys.accessToken,
      value: accessToken,
    );
    try {
      final snap = SessionSecuritySnapshot.fromAccessTokenClaims(accessToken);
      await _storage.write(
        key: SessionStorageKeys.securityClaimsJson,
        value: jsonEncode(snap.toPersistedClaimsJson()),
      );
    } catch (_) {}
    if (refreshToken != null && refreshToken.isNotEmpty) {
      await _storage.write(
        key: SessionStorageKeys.refreshToken,
        value: refreshToken,
      );
    }
    if (accessExpiresAt != null) {
      await _storage.write(
        key: SessionStorageKeys.accessExpiresAtMs,
        value: '${accessExpiresAt.millisecondsSinceEpoch}',
      );
    } else {
      final jexp = jwtExtractExpiryMs(accessToken);
      if (jexp != null) {
        await _storage.write(
          key: SessionStorageKeys.accessExpiresAtMs,
          value: '$jexp',
        );
      }
    }
    if (greetingFirstName != null) {
      final g = greetingFirstName.trim();
      if (g.isEmpty || jwtIsLikelyOpaqueUserIdentifier(g)) {
        await _storage.delete(key: SessionStorageKeys.clientGreetingFirstName);
      } else {
        await _storage.write(
          key: SessionStorageKeys.clientGreetingFirstName,
          value: g,
        );
      }
    } else {
      final fromJwt = extractGreetingFirstNameFromAccessToken(accessToken);
      if (fromJwt != null &&
          fromJwt.isNotEmpty &&
          !jwtIsLikelyOpaqueUserIdentifier(fromJwt)) {
        await _storage.write(
          key: SessionStorageKeys.clientGreetingFirstName,
          value: fromJwt,
        );
      }
    }
    String? mirroredGreeting =
        await _storage.read(key: SessionStorageKeys.clientGreetingFirstName);
    final mg = mirroredGreeting?.trim();
    if (mg != null && jwtIsLikelyOpaqueUserIdentifier(mg)) {
      mirroredGreeting = null;
      await _storage.delete(key: SessionStorageKeys.clientGreetingFirstName);
    }
    await PasscodeClientGreetingStorage.instance.writeForAccessToken(
      accessToken,
      mirroredGreeting,
    );
    SessionIdentityContext.instance.syncFromAccessToken(accessToken);
    if (notifySessionLifecycle) {
      SessionStateMachine.instance.apply(SessionLifecycleEvent.accessTokenPersisted);
    }
  }

  /// Prénom issu du profil mobile (PII) — remplace un stockage erroné (ex. ID client en guise de prénom).
  Future<void> persistGreetingFirstNameFromProfile(String firstName) async {
    final t = firstName.trim();
    if (t.isEmpty || jwtIsLikelyOpaqueUserIdentifier(t)) return;
    final token = await readAccessToken();
    if (token == null) return;
    await _storage.write(
      key: SessionStorageKeys.clientGreetingFirstName,
      value: t,
    );
    await PasscodeClientGreetingStorage.instance.writeForAccessToken(token, t);
  }

  Future<void> _deleteLoginRememberedIdentifiers() async {
    await _storage.delete(key: SessionStorageKeys.loginLastEmail);
    await _storage.delete(key: SessionStorageKeys.loginLastPhoneE164);
  }

  Future<void> clearSession() async {
    SessionIdentityContext.instance.clear();
    CurrencyPreference.instance.resetForLogout();
    ProfileLeadingPreference.instance.resetForLogout();
    await _storage.delete(key: SessionStorageKeys.accessToken);
    await _storage.delete(key: SessionStorageKeys.refreshToken);
    await _storage.delete(key: SessionStorageKeys.accessExpiresAtMs);
    await _storage.delete(key: SessionStorageKeys.clientGreetingFirstName);
    await _storage.delete(key: SessionStorageKeys.pendingEuRegistrationAfterPasscode);
    await _deleteVolatileSessionSecurityKeys();
    await _deleteLoginRememberedIdentifiers();
    SessionStateMachine.instance.apply(
      SessionLifecycleEvent.tokensCleared,
      detail: 'clearSession',
    );
  }

  /// Mémorise les identifiants de connexion (non secrets — confort UX).
  Future<void> rememberLoginIdentifiers({
    String? email,
    String? phoneE164,
  }) async {
    if (email != null && email.trim().isNotEmpty) {
      await _storage.write(
        key: SessionStorageKeys.loginLastEmail,
        value: email.trim().toLowerCase(),
      );
    }
    if (phoneE164 != null && phoneE164.trim().isNotEmpty) {
      await _storage.write(
        key: SessionStorageKeys.loginLastPhoneE164,
        value: phoneE164.trim(),
      );
    }
  }

  Future<String?> readLastLoginEmail() async =>
      await _storage.read(key: SessionStorageKeys.loginLastEmail);

  Future<String?> readLastLoginPhoneE164() async =>
      await _storage.read(key: SessionStorageKeys.loginLastPhoneE164);

  Future<String?> readGreetingFirstName() async =>
      await _storage.read(key: SessionStorageKeys.clientGreetingFirstName);

  /// Présence d’au moins un access token local (ne garantit pas la validité serveur).
  Future<bool> hasSessionCredentials() async {
    final a = await _storage.read(key: SessionStorageKeys.accessToken);
    return a != null && a.isNotEmpty;
  }

  /// Compte app **ACTIVE** (JWT : pas ``sec_inc``, ``acct_st`` absent ou ACTIVE). Aligné backend — pas de seule confiance dans un champ UI.
  Future<bool> isLastStoredAccessAccountActive() async {
    final t = await readAccessToken();
    if (t == null || t.isEmpty) return false;
    return isAccessTokenAccountActiveForApp(t);
  }

  /// Bearer pour appels authentifiés (ex. gestion passkeys).
  Future<String?> readAccessToken() async =>
      await _storage.read(key: SessionStorageKeys.accessToken);

  /// Marque l’intention d’enchaîner [RegistrationFlowScreen] après création du PIN (parcours inscription EU).
  Future<void> setPendingEuRegistrationAfterPasscode(bool value) async {
    if (value) {
      await _storage.write(
        key: SessionStorageKeys.pendingEuRegistrationAfterPasscode,
        value: '1',
      );
    } else {
      await _storage.delete(key: SessionStorageKeys.pendingEuRegistrationAfterPasscode);
    }
  }

  /// Consomme le flag ; retourne true une seule fois.
  Future<bool> consumePendingEuRegistrationAfterPasscode() async {
    final v = await _storage.read(key: SessionStorageKeys.pendingEuRegistrationAfterPasscode);
    await _storage.delete(key: SessionStorageKeys.pendingEuRegistrationAfterPasscode);
    return v == '1';
  }

  /// Indique si un refresh est pertinent (expiration locale connue ou stale).
  Future<bool> shouldRefreshAccessToken() async {
    var expMs = int.tryParse(
      await _storage.read(key: SessionStorageKeys.accessExpiresAtMs) ?? '',
    );
    if (expMs == null) {
      final t = await readAccessToken();
      if (t != null && t.isNotEmpty) {
        expMs = jwtExtractExpiryMs(t);
      }
    }
    // Sans date d’expiration connue : ne pas forcer un refresh (évite un refresh + 401
    // qui effaçait la session au déverrouillage passcode avant d’atteindre la Home).
    if (expMs == null) {
      return false;
    }
    final exp = DateTime.fromMillisecondsSinceEpoch(expMs);
    final now = DateTime.now();
    if (now.isAfter(exp)) return true;
    return exp.difference(now) < SecureAccessConfig.sessionStaleAfter;
  }

  /// Rafraîchit l’access token via FastAPI `/auth/refresh` si une URL auth est résolue ([SecureApiConfig.resolvedAuthApiBaseUrl]).
  ///
  /// Notifie [SessionStateMachine] : `refreshStarted` → `refreshSucceeded` / `refreshFailed` / `refreshAborted`.
  Future<bool> refreshAccessToken() async {
    if (!SecureApiConfig.hasAuthBackend) return false;
    final rt = await _storage.read(key: SessionStorageKeys.refreshToken);
    if (rt == null || rt.isEmpty) return false;

    final machine = SessionStateMachine.instance;
    final refreshTransitionOk =
        machine.apply(SessionLifecycleEvent.refreshStarted);

    try {
      final res = await _api.refresh(refreshToken: rt);
      if (res.statusCode == 401) {
        if (refreshTransitionOk) {
          machine.apply(SessionLifecycleEvent.refreshFailed);
        }
        await clearSession();
        return false;
      }
      if (!res.ok || res.accessToken == null) {
        if (refreshTransitionOk) {
          machine.apply(SessionLifecycleEvent.refreshAborted);
        }
        return false;
      }
      await storeTokens(
        accessToken: res.accessToken!,
        refreshToken: res.refreshToken ?? rt,
        notifySessionLifecycle: false,
      );
      if (refreshTransitionOk) {
        machine.apply(SessionLifecycleEvent.refreshSucceeded);
      } else {
        machine.apply(SessionLifecycleEvent.accessTokenPersisted);
      }
      if (kDebugMode) {
        debugPrint('[SessionService] access token refreshed (opaque)');
      }
      return true;
    } catch (_) {
      if (refreshTransitionOk) {
        machine.apply(SessionLifecycleEvent.refreshAborted);
      }
      return false;
    }
  }

  Future<void> revokeRemoteSession() async {
    if (!SecureApiConfig.hasAuthBackend) {
      await clearSession();
      return;
    }
    final rt = await _storage.read(key: SessionStorageKeys.refreshToken);
    if (rt != null && rt.isNotEmpty) {
      await _api.revoke(refreshToken: rt);
    }
    await clearSession();
  }

  Future<bool> isSessionValid() async {
    if (!await hasSessionCredentials()) return false;
    if (await shouldRefreshAccessToken()) {
      return refreshAccessToken();
    }
    return true;
  }

  /// Snapshot pour la politique de relock (claims JWT persistés + horodatages locaux).
  Future<SessionSecuritySnapshot> readSecuritySnapshot() async {
    final rawClaims = await _storage.read(key: SessionStorageKeys.securityClaimsJson);
    final sensMs = int.tryParse(
      await _storage.read(key: SessionStorageKeys.lastSensitiveActionAtMs) ?? '',
    );
    final unlockMs = int.tryParse(
      await _storage.read(key: SessionStorageKeys.lastLocalUnlockAtMs) ?? '',
    );
    return SessionSecuritySnapshot.fromPersistedClaimsJson(
      rawClaims,
      lastSensitiveActionAt: sensMs != null
          ? DateTime.fromMillisecondsSinceEpoch(sensMs)
          : null,
      lastLocalUnlockAt: unlockMs != null
          ? DateTime.fromMillisecondsSinceEpoch(unlockMs)
          : null,
    );
  }

  /// À appeler après une action sensible (virement, clé API, etc.) — optionnel.
  Future<void> touchSensitiveAction() async {
    await _storage.write(
      key: SessionStorageKeys.lastSensitiveActionAtMs,
      value: '${DateTime.now().millisecondsSinceEpoch}',
    );
  }

  /// Après PIN ou biométrie réussie — alimente le moteur de relock / grace.
  Future<void> recordLocalUnlockSuccess() async {
    await _storage.write(
      key: SessionStorageKeys.lastLocalUnlockAtMs,
      value: '${DateTime.now().millisecondsSinceEpoch}',
    );
    await _storage.write(
      key: SessionStorageKeys.biometricRecentFailCount,
      value: '0',
    );
    await _storage.delete(key: SessionStorageKeys.lastBiometricFailAtMs);
  }

  Future<void> recordBiometricAuthFailure() async {
    final now = DateTime.now().millisecondsSinceEpoch;
    await _storage.write(
      key: SessionStorageKeys.lastBiometricFailAtMs,
      value: '$now',
    );
    final prev = int.tryParse(
          await _storage.read(key: SessionStorageKeys.biometricRecentFailCount) ??
              '0',
        ) ??
        0;
    await _storage.write(
      key: SessionStorageKeys.biometricRecentFailCount,
      value: '${prev + 1}',
    );
  }

  Future<int> readBiometricRecentFailCount() async =>
      int.tryParse(
        await _storage.read(key: SessionStorageKeys.biometricRecentFailCount) ??
            '0',
      ) ??
      0;

  Future<DateTime?> readLastBiometricFailAt() async {
    final ms = int.tryParse(
      await _storage.read(key: SessionStorageKeys.lastBiometricFailAtMs) ?? '',
    );
    if (ms == null) return null;
    return DateTime.fromMillisecondsSinceEpoch(ms);
  }
}
