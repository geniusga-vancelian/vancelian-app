import 'package:flutter/foundation.dart';

import '../../../../core/session/session_lifecycle_state.dart';
import '../../../../core/session/session_state_machine.dart';
import '../../passcode/data/session_service.dart';
import '../application/passkey_service.dart';
import '../data/passkey_api.dart';
import '../domain/passkey_exceptions.dart';

/// Analytics auto-trigger (login téléphone) — best-effort, ne bloque jamais le flux.
typedef PasskeyAutoAnalytics = Future<void> Function(String event, {String? detail});

/// Coordonne login passkey + persistance session ; fallback OTP si indisponible ou erreur.
/// Interruption / background prolongé sur l’écran appelant : voir [AuthFlowLifecycleObserver].
/// (écran e-mail / passkey).
class PasskeyLoginCoordinator {
  PasskeyLoginCoordinator({
    required PasskeyService passkeyService,
    PasskeyApi? api,
  })  : _passkeys = passkeyService,
        _api = api ?? PasskeyApi();

  final PasskeyService _passkeys;
  final PasskeyApi _api;

  static const _opened = 'auth.passkey.prompt.opened';
  static const _cancelled = 'auth.passkey.prompt.cancelled';
  static const _failed = 'auth.passkey.prompt.failed';

  /// [onFallback] : OTP ou autre (ne doit pas bloquer l’utilisateur).
  /// [onSuccess] : navigation post-login.
  /// [autoAnalytics] : événements ``auth.login.passkey_auto_*`` (sécurité / produit).
  Future<void> signInWithPasskey({
    required String email,
    required VoidCallback onFallback,
    required AsyncCallback onSuccess,
    PasskeyAutoAnalytics? autoAnalytics,
  }) async {
    Future<void> fallback() async {
      try {
        await autoAnalytics?.call('auth.login.passkey_auto_trigger_fallback_otp');
      } catch (_) {}
      onFallback();
    }

    try {
      await autoAnalytics?.call('auth.login.passkey_auto_triggered');
    } catch (_) {}

    await _api.reportPrompt(event: _opened, email: email);
    try {
      SessionStateMachine.instance.apply(SessionLifecycleEvent.loginFlowStarted);
      final tokens = await _passkeys.loginWithPasskey(email);
      final at = tokens['access_token'] as String?;
      final rt = tokens['refresh_token'] as String?;
      if (at == null || at.isEmpty) {
        await _api.reportPrompt(event: _failed, email: email, detail: 'missing_access_token');
        try {
          await autoAnalytics?.call(
            'auth.login.passkey_auto_trigger_failed',
            detail: 'missing_access_token',
          );
        } catch (_) {}
        await fallback();
        return;
      }
      await SessionService.instance.storeTokens(
        accessToken: at,
        refreshToken: rt,
      );
      await onSuccess();
    } on PasskeyUserCancelledException catch (_) {
      await _api.reportPrompt(event: _cancelled, email: email);
      try {
        await autoAnalytics?.call('auth.login.passkey_auto_trigger_cancelled');
      } catch (_) {}
      if (kDebugMode) {
        debugPrint('[PasskeyLoginCoordinator] user cancelled');
      }
      await fallback();
    } on PasskeyUnavailableException catch (e) {
      await _api.reportPrompt(event: _failed, email: email, detail: e.message);
      try {
        await autoAnalytics?.call(
          'auth.login.passkey_auto_trigger_failed',
          detail: 'unavailable:${e.message}',
        );
      } catch (_) {}
      if (kDebugMode) {
        debugPrint('[PasskeyLoginCoordinator] unavailable: $e');
      }
      await fallback();
    } on PasskeyAuthenticatorFailureException catch (e) {
      await _api.reportPrompt(event: _failed, email: email, detail: e.message);
      try {
        await autoAnalytics?.call(
          'auth.login.passkey_auto_trigger_failed',
          detail: 'authenticator:${e.message}',
        );
      } catch (_) {}
      if (kDebugMode) {
        debugPrint('[PasskeyLoginCoordinator] authenticator: $e');
      }
      await fallback();
    } on PasskeyApiException catch (e) {
      await _api.reportPrompt(event: _failed, email: email, detail: 'api_${e.statusCode}');
      try {
        await autoAnalytics?.call(
          'auth.login.passkey_auto_trigger_failed',
          detail: 'api_${e.statusCode}',
        );
      } catch (_) {}
      if (kDebugMode) {
        debugPrint('[PasskeyLoginCoordinator] API fallback: $e');
      }
      await fallback();
    } catch (e, st) {
      await _api.reportPrompt(event: _failed, email: email, detail: e.toString());
      try {
        await autoAnalytics?.call('auth.login.passkey_auto_trigger_failed', detail: 'unexpected');
      } catch (_) {}
      if (kDebugMode) {
        debugPrint('[PasskeyLoginCoordinator] unexpected: $e\n$st');
      }
      await fallback();
    }
  }
}
