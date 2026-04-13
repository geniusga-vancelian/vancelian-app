import 'dart:async';
import 'dart:developer' as developer;

import 'package:flutter/material.dart';
import 'package:permission_handler/permission_handler.dart';

import '../../../design_system/atoms/app_colors.dart';
import '../../../design_system/components/app_primary_button.dart';
import '../../../design_system/components/ds_permission_prompt.dart';
import '../../../features/profile/data/mobile_profile_api.dart';
import '../../../features/profile/data/patch_security_preferences_result.dart';
import '../../../features/profile/data/security_preferences_patch_feedback.dart';
import '../../../features/profile/data/security_preferences_post_pop_snackbar.dart';
import '../../../features/profile/data/security_preferences_sync_service.dart';
import '../../../features/profile/domain/security_preferences_payload.dart';
import '../passcode/data/passcode_service.dart';
import '../passcode/data/session_service.dart';
import '../passcode/domain/push_notification_onboarding_prompt_state.dart';
import 'notification_permission_analytics_status.dart';
import 'push_notifications_onboarding_kind.dart';
import 'push_notifications_product_analytics.dart';
import 'push_notification_permission_coordinator.dart';

export 'push_notifications_onboarding_kind.dart';

/// Opt-in notifications : préférence produit vs OS peuvent diverger (aligné backend V1).
class PushNotificationsOnboardingScreen extends StatefulWidget {
  const PushNotificationsOnboardingScreen({
    super.key,
    this.kind = PushNotificationsOnboardingKind.registration,
  });

  final PushNotificationsOnboardingKind kind;

  @override
  State<PushNotificationsOnboardingScreen> createState() =>
      _PushNotificationsOnboardingScreenState();
}

class _PushNotificationsOnboardingScreenState
    extends State<PushNotificationsOnboardingScreen>
    with WidgetsBindingObserver {
  bool _busy = false;
  bool _recordedShown = false;

  /// Après [openAppSettings] : on finalise au retour si l’OS est passé à « autorisé ».
  bool _awaitingReturnFromSettings = false;

  static void _log(String msg, {Map<String, Object?>? data}) {
    developer.log(
      data == null ? msg : '$msg ${data.toString()}',
      name: 'PushOnboarding',
    );
  }

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    WidgetsBinding.instance.addPostFrameCallback((_) => _onFirstFrame());
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    super.didChangeAppLifecycleState(state);
    if (state == AppLifecycleState.resumed) {
      unawaited(_onAppResumedAfterMaybeSettings());
    }
  }

  Future<void> _onAppResumedAfterMaybeSettings() async {
    if (!_awaitingReturnFromSettings || _busy) return;
    final st = await Permission.notification.status;
    if (!mounted) return;
    final ok = st.isGranted || st.isLimited || st.isProvisional;
    if (!ok) return;
    setState(() {
      _awaitingReturnFromSettings = false;
      _busy = true;
    });
    try {
      await _completeEnabledFlow(status: st);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _onFirstFrame() async {
    if (!mounted || _recordedShown) return;
    _recordedShown = true;
    await PasscodeService.instance.init();
    final current = await PasscodeService.instance.getPushOnboardingPromptState();
    PushNotificationsProductAnalytics.pushOnboardingPromptShown(
      source: widget.kind.analyticsSource,
      currentState: current.storageValue,
    );
    await PasscodeService.instance.recordAutomaticPushOnboardingPromptDisplayed();
  }

  Map<String, dynamic> _basePushFields() {
    return <String, dynamic>{
      'last_client_reported_at': securityUtcIsoNow(),
      'onboarding_source': mobileSecurityOnboardingSource(),
    };
  }

  String _osPermissionLastKnown(PermissionStatus s) {
    switch (s) {
      case PermissionStatus.granted:
        return 'granted';
      case PermissionStatus.denied:
      case PermissionStatus.restricted:
      case PermissionStatus.permanentlyDenied:
        return 'denied';
      case PermissionStatus.limited:
        return 'limited';
      case PermissionStatus.provisional:
        return 'provisional';
    }
  }

  Future<PermissionStatus> _currentNotificationStatus() async {
    return Permission.notification.status;
  }

  Future<void> _persistLocalAfterChoice({
    required bool enabled,
  }) async {
    await PasscodeService.instance.init();
    if (enabled) {
      await PasscodeService.instance
          .setPushOnboardingPromptState(PushNotificationOnboardingPromptState.enabled);
      await PasscodeService.instance.setPushNotificationsPreferenceEnabled(true);
    } else {
      await PasscodeService.instance.setPushNotificationsPreferenceEnabled(false);
      await PasscodeService.instance.setPushOnboardingPromptState(
        widget.kind == PushNotificationsOnboardingKind.registration
            ? PushNotificationOnboardingPromptState.skippedRegistration
            : PushNotificationOnboardingPromptState.skippedFirstRelogin,
      );
    }
  }

  Future<String> _resultingStateStorageValue() async {
    final s = await PasscodeService.instance.getPushOnboardingPromptState();
    return s.storageValue;
  }

  Future<void> _syncAfterPop({
    required Map<String, dynamic> pushPayload,
    required ScaffoldMessengerState? messenger,
  }) async {
    const api = MobileProfileApi();
    _log('syncAfterPop', data: {'outcome': pushPayload['onboarding_outcome']});

    final tok = await SessionService.instance.readAccessToken();
    final hasToken = tok != null && tok.isNotEmpty;
    _log('token', data: {'present': hasToken});

    if (!hasToken) {
      SecurityPreferencesSyncService.instance.pushState =
          SecurityDomainSyncState.pendingSync;
      await SecurityPreferencesSyncService.instance.schedulePushRetry(pushPayload);
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
      return;
    }

    final r = await api.patchSecurityPreferencesV1(
      accessToken: tok,
      pushNotifications: pushPayload,
    );
    switch (r) {
      case PatchSecurityPreferencesSuccess():
        SecurityPreferencesSyncService.instance.pushState =
            SecurityDomainSyncState.synced;
        _log('PATCH result', data: {'kind': 'success'});
        return;
      case PatchSecurityPreferencesFailure(
          kind: final kind,
        ):
        SecurityPreferencesSyncService.instance.pushState =
            SecurityDomainSyncState.syncFailed;
        await SecurityPreferencesSyncService.instance.schedulePushRetry(
          pushPayload,
        );
        _log('PATCH result', data: {'kind': kind.name, 'retryScheduled': true});
        final msg = userMessageForPatchSecurityPreferencesFailure(r);
        if (messenger == null) {
          _log('snackbar skipped (no messenger)', data: {'kind': kind.name});
        }
        showSecurityPreferencesPostPopSnackBar(messenger, msg);
    }
  }

  Future<void> _onSkip() async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      final messenger = ScaffoldMessenger.maybeOf(context);
      final st = await _currentNotificationStatus();
      final perm = NotificationPermissionAnalyticsStatus.fromPermissionStatus(st);
      final payload = {
        ..._basePushFields(),
        'preference_enabled': false,
        'onboarding_outcome': 'skipped',
        'os_permission_last_known': _osPermissionLastKnown(st),
      };
      await _persistLocalAfterChoice(enabled: false);
      final resulting = await _resultingStateStorageValue();
      PushNotificationsProductAnalytics.pushOnboardingAction(
        source: widget.kind.analyticsSource,
        action: 'skipped',
        permissionStatus: perm.analyticsValue,
        resultingState: resulting,
      );
      if (!mounted) return;
      Navigator.of(context).pop();
      await _syncAfterPop(pushPayload: payload, messenger: messenger);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _completeEnabledFlow({required PermissionStatus status}) async {
    final messenger = ScaffoldMessenger.maybeOf(context);
    final norm = NotificationPermissionAnalyticsStatus.fromPermissionStatus(status);
    final payload = {
      ..._basePushFields(),
      'preference_enabled': true,
      'onboarding_outcome': 'enabled',
      'os_permission_last_known': _osPermissionLastKnown(status),
    };
    await _persistLocalAfterChoice(enabled: true);
    final resulting = await _resultingStateStorageValue();
    PushNotificationsProductAnalytics.pushOnboardingAction(
      source: widget.kind.analyticsSource,
      action: 'enabled',
      permissionStatus: norm.analyticsValue,
      resultingState: resulting,
    );
    if (!mounted) return;
    Navigator.of(context).pop();
    await _syncAfterPop(pushPayload: payload, messenger: messenger);
  }

  Future<void> _onEnable() async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      final outcome = await PushNotificationPermissionCoordinator.request();
      switch (outcome) {
        case PushNotificationPermissionOutcome.granted:
          final status = await Permission.notification.status;
          if (!mounted) return;
          await _completeEnabledFlow(status: status);
          return;
        case PushNotificationPermissionOutcome.navigatedToSettings:
          final st = await Permission.notification.status;
          final resulting = await _resultingStateStorageValue();
          final norm =
              NotificationPermissionAnalyticsStatus.fromPermissionStatus(st);
          PushNotificationsProductAnalytics.pushOnboardingAction(
            source: widget.kind.analyticsSource,
            action: 'settings_redirect_needed',
            permissionStatus: norm.analyticsValue,
            resultingState: resulting,
          );
          if (mounted) {
            setState(() => _awaitingReturnFromSettings = true);
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                content: Text(
                  'Dans Réglages, activez les notifications pour cette app, puis revenez ici — nous détecterons l’activation automatiquement.',
                ),
                behavior: SnackBarBehavior.floating,
                margin: EdgeInsets.all(16),
              ),
            );
          }
          return;
        case PushNotificationPermissionOutcome.denied:
          final st = await Permission.notification.status;
          final resulting = await _resultingStateStorageValue();
          final norm =
              NotificationPermissionAnalyticsStatus.fromPermissionStatus(st);
          PushNotificationsProductAnalytics.pushOnboardingAction(
            source: widget.kind.analyticsSource,
            action: 'denied',
            permissionStatus: norm.analyticsValue,
            resultingState: resulting,
          );
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                content: Text(
                  'Sans autorisation système, les alertes ne pourront pas s’afficher sur cet appareil.',
                ),
                behavior: SnackBarBehavior.floating,
                margin: EdgeInsets.all(16),
              ),
            );
          }
          return;
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final k = widget.kind;
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (bool didPop, dynamic result) async {
        if (didPop) return;
        if (!_busy) await _onSkip();
      },
      child: Scaffold(
        backgroundColor: AppColors.iosChromeBackground,
        body: SafeArea(
          child: DsPermissionPromptLayout(
            showStatusBar: false,
            title: PushOnboardingCopy.title(k),
            body: PushOnboardingCopy.body(k),
            hero: const DsPermissionHero(
              symbol: Icon(
                Icons.notifications_active_rounded,
                size: 70,
                color: AppColors.indigo,
              ),
              symbolSize: 70,
            ),
            primaryButton: AppPrimaryButton(
              label: PushOnboardingCopy.primaryCta(k),
              onPressed: _busy ? null : _onEnable,
              isLoading: _busy,
            ),
            secondaryButton: AppPrimaryButton(
              label: PushOnboardingCopy.secondaryCta,
              variant: AppPrimaryButtonVariant.secondary,
              onPressed: _busy ? null : _onSkip,
            ),
          ),
        ),
      ),
    );
  }
}
