import 'dart:convert';

import 'package:passkeys/authenticator.dart';
import 'package:passkeys/exceptions.dart' as pe;
import 'package:passkeys/types.dart';

import 'data/passkey_provider.dart';
import 'domain/passkey_exceptions.dart';

/// Passkeys natives via le package `passkeys` (ASAuthorization* iOS, Credential Manager Android).
abstract class _NativePasskeyProviderBase implements PasskeyPlatformProvider {
  _NativePasskeyProviderBase({PasskeyAuthenticator? authenticator})
      : _auth = authenticator ?? PasskeyAuthenticator();

  final PasskeyAuthenticator _auth;

  Future<Map<String, dynamic>> _register(Map<String, dynamic> optionsJson) async {
    try {
      final req = RegisterRequestType.fromJsonString(jsonEncode(optionsJson));
      final res = await _auth.register(req);
      return res.toJson();
    } on pe.PasskeyAuthCancelledException {
      throw PasskeyUserCancelledException();
    } on pe.NoCredentialsAvailableException {
      throw PasskeyUnavailableException('No credential for registration');
    } on pe.DeviceNotSupportedException {
      throw PasskeyUnavailableException('Device does not support passkeys');
    } on pe.PasskeyUnsupportedException catch (e) {
      throw PasskeyUnavailableException(e.toString());
    } on pe.MissingGoogleSignInException {
      throw PasskeyUnavailableException('Google account required for passkeys on this device');
    } on pe.SyncAccountNotAvailableException {
      throw PasskeyUnavailableException('Passkey sync account unavailable');
    } on pe.ExcludeCredentialsCanNotBeRegisteredException {
      throw PasskeyAuthenticatorFailureException('Credential already registered on device');
    } on pe.TimeoutException catch (e) {
      throw PasskeyAuthenticatorFailureException(e.toString());
    } on pe.AuthenticatorException catch (e) {
      throw PasskeyAuthenticatorFailureException(e.toString());
    }
  }

  Future<Map<String, dynamic>> _authenticate(Map<String, dynamic> optionsJson) async {
    try {
      final req = AuthenticateRequestType.fromJsonString(jsonEncode(optionsJson));
      final res = await _auth.authenticate(req);
      return res.toJson();
    } on pe.PasskeyAuthCancelledException {
      throw PasskeyUserCancelledException();
    } on pe.NoCredentialsAvailableException {
      throw PasskeyUnavailableException('No passkey on this device for this account');
    } on pe.DeviceNotSupportedException {
      throw PasskeyUnavailableException('Device does not support passkeys');
    } on pe.PasskeyUnsupportedException catch (e) {
      throw PasskeyUnavailableException(e.toString());
    } on pe.DomainNotAssociatedException catch (e) {
      throw PasskeyAuthenticatorFailureException(e.toString());
    } on pe.NoCreateOptionException catch (e) {
      throw PasskeyAuthenticatorFailureException(e.toString());
    } on pe.TimeoutException catch (e) {
      throw PasskeyAuthenticatorFailureException(e.toString());
    } on pe.AuthenticatorException catch (e) {
      throw PasskeyAuthenticatorFailureException(e.toString());
    }
  }

  @override
  Future<Map<String, dynamic>> createCredential(Map<String, dynamic> optionsJson) =>
      _register(optionsJson);

  @override
  Future<Map<String, dynamic>> getCredential(Map<String, dynamic> optionsJson) =>
      _authenticate(optionsJson);
}

/// iOS — ``ASAuthorizationController`` / passkeys (via plugin).
class IOSPasskeyProvider extends _NativePasskeyProviderBase {
  IOSPasskeyProvider({super.authenticator});

  @override
  Future<bool> get isAvailable async {
    try {
      final ios = await _auth.getAvailability().iOS();
      return ios.hasPasskeySupport;
    } catch (_) {
      return false;
    }
  }
}

/// Android — Credential Manager (plugin) avec contrôle disponibilité plateforme.
class AndroidPasskeyProvider extends _NativePasskeyProviderBase {
  AndroidPasskeyProvider({super.authenticator});

  @override
  Future<bool> get isAvailable async {
    try {
      final a = await _auth.getAvailability().android();
      if (!a.hasPasskeySupport) return false;
      final uv = a.isUserVerifyingPlatformAuthenticatorAvailable;
      return uv != false;
    } catch (_) {
      return false;
    }
  }
}
