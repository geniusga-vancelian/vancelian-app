import 'dart:developer' as developer;

import 'dart:io' show Platform;

import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:local_auth/local_auth.dart';

/// Icône affichée sur le pavé PIN (gauche du « 0 »).
enum BiometricKeypadIconKind {
  face,
  fingerprint,
}

/// Face ID / Touch ID / biométrie forte — sans journaliser le résultat détaillé en prod.
class BiometricAuthService {
  BiometricAuthService._();
  static final BiometricAuthService instance = BiometricAuthService._();

  final LocalAuthentication _auth = LocalAuthentication();

  Future<bool> deviceSupportsBiometrics() async {
    try {
      final supported = await _auth.isDeviceSupported();
      final can = await _auth.canCheckBiometrics;
      return supported && can;
    } on PlatformException {
      return false;
    }
  }

  Future<bool> authenticate({required String reason}) async {
    try {
      final result = await _auth.authenticate(
        localizedReason: reason,
        options: const AuthenticationOptions(
          biometricOnly: true,
          stickyAuth: true,
        ),
      );
      return result;
    } on PlatformException catch (e, st) {
      // Diagnostiquer prompt iOS absent vs annulation (codes typiques : UserCancel, NotAvailable…)
      developer.log(
        'LocalAuthentication PlatformException code=${e.code} message=${e.message}',
        name: 'BiometricAuth',
        error: e,
        stackTrace: st,
      );
      debugPrint(
        '[BiometricAuth] PlatformException code=${e.code} message=${e.message}',
      );
      return false;
    }
  }

  /// Libellé court pour l’UI (sans jargon technique).
  Future<String> primaryUnlockLabel() async {
    try {
      final types = await _auth.getAvailableBiometrics();
      if (types.contains(BiometricType.face)) {
        return 'Face ID';
      }
      if (types.contains(BiometricType.iris)) {
        return 'Reconnaissance oculaire';
      }
      if (types.contains(BiometricType.fingerprint) ||
          types.contains(BiometricType.strong)) {
        if (!kIsWeb && Platform.isIOS) {
          return 'Touch ID';
        }
        return 'Empreinte';
      }
    } on PlatformException {
      return 'Biométrie';
    }
    return 'Biométrie';
  }

  /// Pour le pavé numérique : Face ID / reconnaissance faciale vs empreinte (Touch ID, Android).
  Future<BiometricKeypadIconKind?> keypadIconKind() async {
    try {
      final types = await _auth.getAvailableBiometrics();
      if (types.contains(BiometricType.face) ||
          types.contains(BiometricType.iris)) {
        return BiometricKeypadIconKind.face;
      }
      if (types.contains(BiometricType.fingerprint) ||
          types.contains(BiometricType.strong)) {
        return BiometricKeypadIconKind.fingerprint;
      }
    } on PlatformException {
      return null;
    }
    return null;
  }
}
