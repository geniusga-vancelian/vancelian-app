import 'dart:developer' as developer;

import 'package:flutter/material.dart';

import '../../../design_system/atoms/app_colors.dart';
import '../../../design_system/components/app_primary_button.dart';
import '../../../design_system/components/ds_permission_prompt.dart';
import '../../../features/profile/data/mobile_profile_api.dart';
import '../../../features/profile/data/patch_security_preferences_result.dart';
import '../../../features/profile/data/security_preferences_patch_feedback.dart';
import '../../../features/profile/data/security_preferences_post_pop_snackbar.dart';
import '../../../features/profile/data/security_preferences_sync_service.dart';
import '../../../features/profile/domain/security_preferences_payload.dart';
import '../passcode/data/biometric_auth_service.dart';
import '../passcode/domain/biometric_onboarding_prompt_state.dart';
import '../passcode/data/passcode_service.dart';
import '../passcode/data/session_service.dart';

/// Face ID / empreinte : local-first ; PATCH V1 structuré ; pas de rollback si PATCH échoue après succès local.
///
/// L’état [BiometricOnboardingPromptState] pilote les ré-invitations : « Plus tard » = skipped
/// (re-demander au prochain déverrouillage) ; indisponible = unavailable ; annulation OS = pas de persistance.
class BiometricLoginOnboardingScreen extends StatefulWidget {
  const BiometricLoginOnboardingScreen({super.key});

  @override
  State<BiometricLoginOnboardingScreen> createState() =>
      _BiometricLoginOnboardingScreenState();
}

class _BiometricLoginOnboardingScreenState
    extends State<BiometricLoginOnboardingScreen> {
  bool _busy = false;
  String _primaryLabel = 'Activer la biométrie';
  bool _deviceOk = false;

  static void _log(String msg, {Map<String, Object?>? data}) {
    developer.log(
      data == null ? msg : '$msg ${data.toString()}',
      name: 'BiometricOnboarding',
    );
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _prepare());
  }

  Future<void> _prepare() async {
    final ok = await BiometricAuthService.instance.deviceSupportsBiometrics();
    final label = await BiometricAuthService.instance.primaryUnlockLabel();
    if (!mounted) return;
    setState(() {
      _deviceOk = ok;
      _primaryLabel = ok ? 'Activer $label' : 'Continuer';
    });
    _log('prepare', data: {'deviceOk': ok, 'label': label});
  }

  Map<String, dynamic> _baseBiometricFields() {
    return <String, dynamic>{
      'last_client_reported_at': securityUtcIsoNow(),
      'onboarding_source': mobileSecurityOnboardingSource(),
    };
  }

  /// Aligné backend : jamais ``unavailable`` + ``available`` (422).
  Map<String, dynamic> _payloadSkipped() {
    if (_deviceOk) {
      return {
        ..._baseBiometricFields(),
        'preference_enabled': false,
        'onboarding_outcome': 'skipped',
        'device_capability_last_known': 'available',
      };
    }
    return {
      ..._baseBiometricFields(),
      'preference_enabled': false,
      'onboarding_outcome': 'unavailable',
      'device_capability_last_known': 'unavailable',
    };
  }

  Map<String, dynamic> _payloadEnabled() {
    return {
      ..._baseBiometricFields(),
      'preference_enabled': true,
      'onboarding_outcome': 'enabled',
      'device_capability_last_known': 'available',
    };
  }

  Future<void> _persistPromptState(BiometricOnboardingPromptState state) async {
    await PasscodeService.instance.init();
    await PasscodeService.instance.setBiometricOnboardingPromptState(state);
    _log('local prompt state', data: {'state': state.storageValue});
  }

  Future<void> _syncAfterPop({
    required Map<String, dynamic> biometricPayload,
    required ScaffoldMessengerState? messenger,
  }) async {
    const api = MobileProfileApi();
    _log('syncAfterPop start', data: {
      'preferenceEnabled': biometricPayload['preference_enabled'],
      'outcome': biometricPayload['onboarding_outcome'],
    });

    final tok = await SessionService.instance.readAccessToken();
    final hasToken = tok != null && tok.isNotEmpty;
    _log('token', data: {'present': hasToken});

    if (!hasToken) {
      SecurityPreferencesSyncService.instance.biometricState =
          SecurityDomainSyncState.pendingSync;
      await SecurityPreferencesSyncService.instance
          .scheduleBiometricRetry(biometricPayload);
      _log('sync deferred: token absent, retry scheduled');
      if (messenger == null) {
        _log('snackbar skipped (no messenger)', data: {'reason': 'token_absent'});
      }
      showSecurityPreferencesPostPopSnackBar(
        messenger,
        userMessageForPatchSecurityPreferencesFailure(
          const PatchSecurityPreferencesFailure(
            PatchSecurityPreferencesFailureKind.sessionMissing,
            detail: 'no_access_token',
          ),
        ),
      );
      _log('snackbar scheduled', data: {'reason': 'token_absent'});
      return;
    }

    final r = await api.patchSecurityPreferencesV1(
      accessToken: tok,
      biometric: biometricPayload,
    );
    switch (r) {
      case PatchSecurityPreferencesSuccess():
        SecurityPreferencesSyncService.instance.biometricState =
            SecurityDomainSyncState.synced;
        _log('PATCH result', data: {'kind': 'success'});
        return;
      case PatchSecurityPreferencesFailure(
          kind: final kind,
          detail: final detail,
        ):
        SecurityPreferencesSyncService.instance.biometricState =
            SecurityDomainSyncState.syncFailed;
        await SecurityPreferencesSyncService.instance.scheduleBiometricRetry(
          biometricPayload,
        );
        _log('PATCH result', data: {
          'kind': kind.name,
          if (detail != null) 'detail': detail,
          'retryScheduled': true,
        });
        final msg = userMessageForPatchSecurityPreferencesFailure(r);
        if (messenger == null) {
          _log('snackbar skipped (no messenger)', data: {'kind': kind.name});
        } else if (suppressSecurityPreferencesFailureSnackBar(r)) {
          _log('snackbar suppressed (endpoint missing / 404, retry scheduled)', data: {
            'kind': kind.name,
          });
        } else {
          showSecurityPreferencesPostPopSnackBar(messenger, msg);
          _log('snackbar scheduled', data: {'kind': kind.name});
        }
    }
  }

  Future<void> _onSkip() async {
    if (_busy) return;
    _log('onSkip enter', data: {'deviceOk': _deviceOk});
    setState(() => _busy = true);
    try {
      final messenger = ScaffoldMessenger.maybeOf(context);
      await _persistPromptState(
        _deviceOk
            ? BiometricOnboardingPromptState.skipped
            : BiometricOnboardingPromptState.unavailable,
      );
      await PasscodeService.instance.setBiometricUnlockEnabled(false);
      _log('local biometric pref', data: {'enabled': false});
      final payload = _payloadSkipped();
      if (!mounted) return;
      Navigator.of(context).pop();
      await _syncAfterPop(biometricPayload: payload, messenger: messenger);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _onPrimary() async {
    if (_busy) return;
    _log('onPrimary enter', data: {'deviceOk': _deviceOk});
    if (!_deviceOk) {
      await _onSkip();
      return;
    }
    setState(() => _busy = true);
    try {
      final messenger = ScaffoldMessenger.maybeOf(context);
      final ok = await BiometricAuthService.instance.authenticate(
        reason: 'Activer le déverrouillage par biométrie',
      );
      _log('biometricAuth', data: {'success': ok});
      if (!mounted) return;
      if (!ok) {
        // Annulation prompt OS : ne pas persister enabled/skipped — ré-invitation possible.
        setState(() => _busy = false);
        return;
      }
      if (!mounted) return;
      await _persistPromptState(BiometricOnboardingPromptState.enabled);
      await PasscodeService.instance.setBiometricUnlockEnabled(true);
      _log('local biometric pref', data: {'enabled': true});
      final payload = _payloadEnabled();
      if (!mounted) return;
      Navigator.of(context).pop();
      await _syncAfterPop(biometricPayload: payload, messenger: messenger);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false,
      child: Scaffold(
        backgroundColor: AppColors.iosChromeBackground,
        body: SafeArea(
          child: DsPermissionPromptLayout(
            showStatusBar: false,
            title: 'Déverrouillage rapide',
            body: _deviceOk
                ? 'Utilisez la biométrie pour ouvrir l’app sans saisir votre code à chaque fois.'
                : 'La biométrie n’est pas disponible sur cet appareil. Vous pourrez activer cette option plus tard dans les réglages de l’app.',
            hero: const DsPermissionHero(),
            primaryButton: AppPrimaryButton(
              label: _primaryLabel,
              onPressed: _busy ? null : _onPrimary,
              isLoading: _busy,
            ),
            secondaryButton: AppPrimaryButton(
              label: 'Plus tard',
              variant: AppPrimaryButtonVariant.secondary,
              onPressed: _busy ? null : _onSkip,
            ),
          ),
        ),
      ),
    );
  }
}
