import 'dart:async';

import 'package:flutter/material.dart';

import '../../../security/passcode/data/biometric_auth_service.dart';
import '../../../security/passcode/data/passcode_service.dart';
import '../../../security/passcode/data/session_service.dart';
import '../../../security/passcode/domain/biometric_onboarding_prompt_state.dart';
import '../../data/mobile_profile_api.dart';
import '../../data/security_preferences_sync_service.dart';
import '../../domain/security_preferences_payload.dart';
import '../../../../design_system/design_system.dart';

/// Réglage local Face ID / Touch ID — état [PasscodeService] uniquement pour l’UI.
///
/// **Désactivation (OFF) et [BiometricOnboardingPromptState.skipped] :** conserver ce mapping
/// est volontaire : l’utilisateur a refusé la biométrie dans les réglages, ce qui aligne le
/// produit sur la même sémantique que « Plus tard » à l’onboarding — le gate login peut
/// **re-proposer** l’activation tant que la politique backend / produit le permet.
/// Ce n’est pas un « opt-out définitif des suggestions » : désactiver Face ID ici ne coupe
/// pas automatiquement les futures invitations à l’activer après déverrouillage.
class AuthenticationMethodsScreen extends StatefulWidget {
  const AuthenticationMethodsScreen({super.key});

  @override
  State<AuthenticationMethodsScreen> createState() =>
      _AuthenticationMethodsScreenState();
}

class _AuthenticationMethodsScreenState extends State<AuthenticationMethodsScreen>
    with WidgetsBindingObserver {
  bool _loading = true;
  bool _busy = false;
  bool _enabled = false;
  bool _deviceOk = false;
  BiometricKeypadIconKind? _iconKind;
  String _bioLabel = 'Biométrie';

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    WidgetsBinding.instance.addPostFrameCallback((_) => _load());
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      _load();
    }
  }

  Future<void> _load() async {
    await PasscodeService.instance.init();
    final deviceOk =
        await BiometricAuthService.instance.deviceSupportsBiometrics();
    await PasscodeService.instance
        .syncBiometricOnboardingPromptStateWithDeviceCapability(deviceOk);
    final bioOn = await PasscodeService.instance.isBiometricUnlockEnabled();
    final label = await BiometricAuthService.instance.primaryUnlockLabel();
    BiometricKeypadIconKind? kind;
    if (deviceOk) {
      kind = await BiometricAuthService.instance.keypadIconKind() ??
          BiometricKeypadIconKind.fingerprint;
    }
    if (!mounted) return;
    setState(() {
      _deviceOk = deviceOk;
      _enabled = bioOn;
      _iconKind = kind;
      _bioLabel = label;
      _loading = false;
    });
  }

  Map<String, dynamic> _patchPayload({required bool enabled}) {
    return <String, dynamic>{
      'last_client_reported_at': securityUtcIsoNow(),
      'onboarding_source': mobileSecurityOnboardingSource(),
      'preference_enabled': enabled,
      'onboarding_outcome': enabled ? 'enabled' : 'skipped',
      'device_capability_last_known': _deviceOk ? 'available' : 'unavailable',
    };
  }

  /// Best-effort : aligné onboarding ; ne bloque jamais l’UI.
  void _optionalPatchInBackground({required bool enabled}) {
    unawaited(_patchBiometricBestEffort(enabled: enabled));
  }

  void _showBiometricEnableFailedFeedback() {
    if (!mounted) return;
    final messenger = ScaffoldMessenger.of(context);
    messenger.hideCurrentSnackBar();
    final bottomInset = MediaQuery.paddingOf(context).bottom + AppSpacing.lg;
    messenger.showSnackBar(
      SnackBar(
        elevation: 0,
        backgroundColor: Colors.transparent,
        padding: EdgeInsets.zero,
        behavior: SnackBarBehavior.floating,
        margin: EdgeInsets.fromLTRB(
          AppSpacing.pageEdge,
          0,
          AppSpacing.pageEdge,
          bottomInset,
        ),
        duration: const Duration(seconds: 3),
        content: AppSnackbar(
          text: 'Authentification annulée',
          variant: AppSnackbarVariant.dark,
        ),
      ),
    );
  }

  Future<void> _patchBiometricBestEffort({required bool enabled}) async {
    final payload = _patchPayload(enabled: enabled);
    final tok = await SessionService.instance.readAccessToken();
    if (tok == null || tok.isEmpty) {
      await SecurityPreferencesSyncService.instance.scheduleBiometricRetry(payload);
      return;
    }
    const api = MobileProfileApi();
    final r = await api.patchSecurityPreferencesV1(
      accessToken: tok,
      biometric: payload,
    );
    if (r.isSuccess) {
      SecurityPreferencesSyncService.instance.biometricState =
          SecurityDomainSyncState.synced;
    } else {
      SecurityPreferencesSyncService.instance.biometricState =
          SecurityDomainSyncState.syncFailed;
      await SecurityPreferencesSyncService.instance.scheduleBiometricRetry(payload);
    }
  }

  Future<void> _onToggleRequested(bool next) async {
    if (_busy) return;
    if (next && !_deviceOk) return;

    if (next) {
      setState(() => _busy = true);
      final ok = await BiometricAuthService.instance.authenticate(
        reason: 'Activer le déverrouillage par biométrie',
      );
      if (!mounted) return;
      if (ok) {
        await PasscodeService.instance.setBiometricUnlockEnabled(true);
        await PasscodeService.instance
            .setBiometricOnboardingPromptState(BiometricOnboardingPromptState.enabled);
        setState(() {
          _enabled = true;
          _busy = false;
        });
        _optionalPatchInBackground(enabled: true);
      } else {
        setState(() => _busy = false);
        _showBiometricEnableFailedFeedback();
      }
      return;
    }

    final confirm = await DsTextConfirmModale.show(
      context,
      title: 'Désactiver $_bioLabel ?',
      message:
          'Vous devrez saisir votre code à chaque connexion.',
      cancelLabel: 'Annuler',
      confirmLabel: 'Désactiver',
    );
    if (!mounted) return;
    if (confirm != true) return;

    setState(() => _busy = true);
    await PasscodeService.instance.setBiometricUnlockEnabled(false);
    // Volontaire : [skipped] = même branche que « Plus tard » onboarding — re-invitation
    // possible au login selon politique produit (voir doc de classe).
    await PasscodeService.instance
        .setBiometricOnboardingPromptState(BiometricOnboardingPromptState.skipped);
    if (!mounted) return;
    setState(() {
      _enabled = false;
      _busy = false;
    });
    _optionalPatchInBackground(enabled: false);
  }

  Widget _leadingBioIcon() {
    final k = _iconKind;
    if (k == BiometricKeypadIconKind.face) {
      return const Icon(
        Icons.face_outlined,
        size: 24,
        color: AppColors.textPrimary,
      );
    }
    return const Icon(
      Icons.fingerprint,
      size: 24,
      color: AppColors.textPrimary,
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const PageSimpleNavBarTopTitlePageContent(
        pageTitle: 'Méthodes de connexion',
        content: [
          SizedBox(height: AppSpacing.xxl),
          Center(child: CircularProgressIndicator()),
        ],
      );
    }

    final toggleValue = _enabled;
    final subtitle =
        !_deviceOk ? 'Face ID n’est pas disponible sur cet appareil' : null;

    return PageSimpleNavBarTopTitlePageContent(
      pageTitle: 'Méthodes de connexion',
      content: [
        const SizedBox(height: AppSpacing.md),
        Text(
          'Choisissez vos méthodes d’authentification préférées pour vous connecter.',
          style: AppTypography.paragraph.copyWith(
            color: AppColors.textSecondary,
            height: 1.45,
          ),
        ),
        const SizedBox(height: AppSpacing.xxl),
        SettingsCard(
          children: [
            SettingsListItem(
              leading: _leadingBioIcon(),
              title: 'Se connecter avec $_bioLabel',
              subtitle: subtitle,
              trailing: AppToggleSwitch(
                value: toggleValue,
                disabled: _busy || !_deviceOk,
                onChanged: (v) => _onToggleRequested(v),
              ),
            ),
          ],
        ),
        const SizedBox(height: AppSpacing.xxl),
        SettingsCard(
          children: [
            SettingsListItem(
              leading: Icon(
                Icons.apple,
                size: 24,
                color: AppColors.textSecondary.withValues(alpha: 0.45),
              ),
              title: 'Se connecter avec Apple',
              subtitle: 'Bientôt disponible',
              showChevron: false,
            ),
          ],
        ),
      ],
    );
  }
}
