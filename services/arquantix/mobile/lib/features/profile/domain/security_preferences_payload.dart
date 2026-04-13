import 'dart:io' show Platform;

import 'package:flutter/foundation.dart' show kIsWeb;

/// Horodatage client pour ``last_client_reported_at`` (UTC, ISO 8601).
String securityUtcIsoNow() =>
    DateTime.now().toUtc().toIso8601String();

/// ``onboarding_source`` pour l’app mobile native.
String mobileSecurityOnboardingSource() {
  if (kIsWeb) {
    return 'web';
  }
  try {
    return Platform.isIOS ? 'app_ios' : 'app_android';
  } on Object {
    return 'unknown';
  }
}
