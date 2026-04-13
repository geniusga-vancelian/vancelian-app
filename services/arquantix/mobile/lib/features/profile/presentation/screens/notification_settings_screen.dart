import 'dart:async';

import 'package:flutter/material.dart';
import 'package:permission_handler/permission_handler.dart';

import '../../../../design_system/design_system.dart';
import '../../data/mobile_profile_api.dart';
import '../../data/patch_security_preferences_result.dart';
import '../../data/security_preferences_patch_feedback.dart';
import '../../data/security_preferences_sync_service.dart';
import '../../domain/security_preferences_payload.dart';
import '../../../security/passcode/data/passcode_service.dart';
import '../../../security/onboarding/notification_permission_analytics_status.dart';
import '../../../security/onboarding/push_notifications_product_analytics.dart';
import '../../../security/passcode/data/session_service.dart';
import '../../../security/passcode/domain/push_notification_onboarding_prompt_state.dart';
import '../../../security/onboarding/push_notification_permission_coordinator.dart';

/// Réglages notifications — interrupteur global « toutes les notifications ».
class NotificationSettingsScreen extends StatefulWidget {
  const NotificationSettingsScreen({super.key});

  @override
  State<NotificationSettingsScreen> createState() =>
      _NotificationSettingsScreenState();
}

class _NotificationSettingsScreenState extends State<NotificationSettingsScreen>
    with WidgetsBindingObserver {
  bool _loading = true;
  bool _toggleValue = false;
  bool _saving = false;

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
    super.didChangeAppLifecycleState(state);
    if (state == AppLifecycleState.resumed) {
      unawaited(_load());
    }
  }

  Future<void> _load() async {
    await PasscodeService.instance.init();
    final pref = await PasscodeService.instance.getPushNotificationsPreferenceEnabled();
    final os = await Permission.notification.status;
    if (!mounted) return;
    setState(() {
      _toggleValue = pref && (os.isGranted || os.isLimited || os.isProvisional);
      _loading = false;
    });
  }

  Map<String, dynamic> _pushPayload({
    required bool preferenceEnabled,
    required PermissionStatus status,
    required String onboardingOutcome,
  }) {
    return <String, dynamic>{
      ...{
        'last_client_reported_at': securityUtcIsoNow(),
        'onboarding_source': mobileSecurityOnboardingSource(),
      },
      'preference_enabled': preferenceEnabled,
      'onboarding_outcome': onboardingOutcome,
      'os_permission_last_known': _osPermissionLastKnown(status),
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

  Future<void> _onToggle(bool wantOn) async {
    if (_saving) return;
    setState(() => _saving = true);
    try {
      if (wantOn) {
        final outcome = await PushNotificationPermissionCoordinator.request();
        if (!mounted) return;
        final st = await Permission.notification.status;
        final granted = st.isGranted || st.isLimited || st.isProvisional;
        if (!granted) {
          final perm =
              NotificationPermissionAnalyticsStatus.fromPermissionStatus(st);
          PushNotificationsProductAnalytics.pushNotificationsSettingsToggled(
            targetValue: wantOn,
            permissionStatus: perm.analyticsValue,
            syncAttempted: false,
          );
          setState(() {
            _toggleValue = false;
            _saving = false;
          });
          if (!mounted) return;
          final msg = outcome == PushNotificationPermissionOutcome.denied
              ? 'Réglages non ouverts — réessayez ou modifiez les notifications dans les paramètres système.'
              : 'Une fois les notifications activées dans Réglages, revenez ici : le statut se mettra à jour au prochain chargement.';
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(msg),
              behavior: SnackBarBehavior.floating,
              margin: const EdgeInsets.all(AppSpacing.md),
            ),
          );
          return;
        }
        await PasscodeService.instance.setPushNotificationsPreferenceEnabled(true);
        await PasscodeService.instance
            .setPushOnboardingPromptState(PushNotificationOnboardingPromptState.enabled);
        setState(() => _toggleValue = true);
        final syncOk = await _syncPushBestEffort(
          preferenceEnabled: true,
          status: st,
          onboardingOutcome: 'enabled',
        );
        final perm =
            NotificationPermissionAnalyticsStatus.fromPermissionStatus(st);
        PushNotificationsProductAnalytics.pushNotificationsSettingsToggled(
          targetValue: true,
          permissionStatus: perm.analyticsValue,
          syncAttempted: syncOk,
        );
      } else {
        await PasscodeService.instance.setPushNotificationsPreferenceEnabled(false);
        final st = await Permission.notification.status;
        if (!mounted) return;
        setState(() => _toggleValue = false);
        final syncOk = await _syncPushBestEffort(
          preferenceEnabled: false,
          status: st,
          onboardingOutcome: 'disabled',
        );
        final perm =
            NotificationPermissionAnalyticsStatus.fromPermissionStatus(st);
        PushNotificationsProductAnalytics.pushNotificationsSettingsToggled(
          targetValue: false,
          permissionStatus: perm.analyticsValue,
          syncAttempted: syncOk,
        );
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  /// `true` si une tentative de synchronisation (PATCH ou file d’attente) a été lancée.
  Future<bool> _syncPushBestEffort({
    required bool preferenceEnabled,
    required PermissionStatus status,
    required String onboardingOutcome,
  }) async {
    final payload = _pushPayload(
      preferenceEnabled: preferenceEnabled,
      status: status,
      onboardingOutcome: onboardingOutcome,
    );
    final tok = await SessionService.instance.readAccessToken();
    if (tok == null || tok.isEmpty) {
      SecurityPreferencesSyncService.instance.pushState =
          SecurityDomainSyncState.pendingSync;
      await SecurityPreferencesSyncService.instance.schedulePushRetry(payload);
      return true;
    }
    const api = MobileProfileApi();
    final r = await api.patchSecurityPreferencesV1(
      accessToken: tok,
      pushNotifications: payload,
    );
    switch (r) {
      case PatchSecurityPreferencesSuccess():
        SecurityPreferencesSyncService.instance.pushState =
            SecurityDomainSyncState.synced;
        return true;
      case PatchSecurityPreferencesFailure():
        SecurityPreferencesSyncService.instance.pushState =
            SecurityDomainSyncState.syncFailed;
        await SecurityPreferencesSyncService.instance.schedulePushRetry(payload);
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(
                userMessageForPatchSecurityPreferencesFailure(r),
              ),
              behavior: SnackBarBehavior.floating,
              margin: const EdgeInsets.all(AppSpacing.md),
            ),
          );
        }
        return true;
    }
  }

  @override
  Widget build(BuildContext context) {
    return PageSimpleNavBarTopTitlePageContent(
      pageTitle: 'Notifications',
      content: [
        if (_loading)
          const Padding(
            padding: EdgeInsets.only(top: AppSpacing.xxl),
            child: Center(
              child: SizedBox(
                width: 24,
                height: 24,
                child: CircularProgressIndicator(strokeWidth: 2),
              ),
            ),
          )
        else ...[
          Text(
            'Choisissez si vous souhaitez recevoir des alertes sur cet appareil.',
            style: AppTypography.itemSupporting.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: AppSpacing.xxl),
          SettingsCard(
            children: [
              SettingsListItem(
                title: 'Toutes les notifications',
                subtitle: 'Alertes compte, marchés et messages importants',
                trailing: _saving
                    ? const SizedBox(
                        width: 22,
                        height: 22,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : AppToggleSwitch(
                        value: _toggleValue,
                        disabled: _saving,
                        onChanged: (v) {
                          unawaited(_onToggle(v));
                        },
                      ),
              ),
            ],
          ),
        ],
      ],
    );
  }
}
