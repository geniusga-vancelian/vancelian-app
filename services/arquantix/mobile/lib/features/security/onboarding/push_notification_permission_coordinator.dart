import 'package:permission_handler/permission_handler.dart';

/// Résultat d’une tentative d’accès aux notifications (aligné UX « apps premium »).
enum PushNotificationPermissionOutcome {
  /// Autorisation accordée (y compris iOS limited / provisional).
  granted,

  /// Refus : on a tenté d’ouvrir **Réglages** pour cette app (succès de [openAppSettings]).
  /// L’app doit souvent finaliser au **retour au premier plan** (lifecycle).
  navigatedToSettings,

  /// Refus sans pouvoir ouvrir les réglages (rare) ou utilisateur revenu sans activer.
  denied,
}

/// Flux unique pour demander la permission notifications + repli **Réglages**.
///
/// **iOS** : la ligne « Notifications » sous Réglages > [app] n’existe qu’après
/// enregistrement système (`registerForRemoteNotifications` — voir `ios/Runner/AppDelegate.swift`).
///
/// Comportement cible :
/// 1. Si déjà autorisé → [PushNotificationPermissionOutcome.granted] sans dialogue.
/// 2. Sinon → [Permission.notification.request] (dialogue système la 1ʳᵉ fois).
/// 3. Si toujours refusé → [openAppSettings] pour cette app (iOS / Android),
///    car souvent le dialogue ne réapparaît plus après un premier « Ne pas autoriser ».
abstract final class PushNotificationPermissionCoordinator {
  PushNotificationPermissionCoordinator._();

  static bool _isOsGranted(PermissionStatus s) =>
      s.isGranted || s.isLimited || s.isProvisional;

  /// Demande l’autorisation ; si refus, ouvre les réglages app quand [openSettingsIfDenied].
  static Future<PushNotificationPermissionOutcome> request({
    bool openSettingsIfDenied = true,
  }) async {
    var status = await Permission.notification.status;
    if (_isOsGranted(status)) {
      return PushNotificationPermissionOutcome.granted;
    }

    status = await Permission.notification.request();
    if (_isOsGranted(status)) {
      return PushNotificationPermissionOutcome.granted;
    }

    if (!openSettingsIfDenied) {
      return PushNotificationPermissionOutcome.denied;
    }

    final opened = await openAppSettings();
    return opened
        ? PushNotificationPermissionOutcome.navigatedToSettings
        : PushNotificationPermissionOutcome.denied;
  }
}
