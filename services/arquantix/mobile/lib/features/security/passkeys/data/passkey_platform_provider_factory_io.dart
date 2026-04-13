import 'dart:io' show Platform;

import 'package:flutter/foundation.dart' show kIsWeb;

import '../passkey_native_provider.dart';
import 'passkey_provider.dart';
import 'passkey_provider_stub.dart';

/// iOS / Android → natif ; web & desktop → stub (OTP / mot de passe).
PasskeyPlatformProvider createPasskeyProvider() {
  if (kIsWeb) return PasskeyProviderStub();
  if (Platform.isIOS) return IOSPasskeyProvider();
  if (Platform.isAndroid) return AndroidPasskeyProvider();
  return PasskeyProviderStub();
}
