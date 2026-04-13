import 'package:permission_handler/permission_handler.dart';

/// Statut normalisé pour analytics / UI (aligné produit).
enum NotificationPermissionAnalyticsStatus {
  granted,
  denied,
  permanentlyDenied,
  provisional,
  unknown;

  String get analyticsValue {
    switch (this) {
      case NotificationPermissionAnalyticsStatus.granted:
        return 'granted';
      case NotificationPermissionAnalyticsStatus.denied:
        return 'denied';
      case NotificationPermissionAnalyticsStatus.permanentlyDenied:
        return 'permanently_denied';
      case NotificationPermissionAnalyticsStatus.provisional:
        return 'provisional';
      case NotificationPermissionAnalyticsStatus.unknown:
        return 'unknown';
    }
  }

  /// Map depuis [Permission.notification] (permission_handler).
  static NotificationPermissionAnalyticsStatus fromPermissionStatus(
    PermissionStatus s,
  ) {
    switch (s) {
      case PermissionStatus.granted:
        return NotificationPermissionAnalyticsStatus.granted;
      case PermissionStatus.permanentlyDenied:
        return NotificationPermissionAnalyticsStatus.permanentlyDenied;
      case PermissionStatus.provisional:
        return NotificationPermissionAnalyticsStatus.provisional;
      case PermissionStatus.limited:
        return NotificationPermissionAnalyticsStatus.granted;
      case PermissionStatus.denied:
        return NotificationPermissionAnalyticsStatus.denied;
      case PermissionStatus.restricted:
        return NotificationPermissionAnalyticsStatus.unknown;
    }
  }
}
