/// Identifiants compilés **sans secrets serveur** (vocation publique côté Privy).
///
/// Build — soit **`--dart-define=...`** en ligne de commande, soit fichier
/// **`services/arquantix/mobile/.env.flutter`** (voir `.env.flutter.example`) lu par
/// `run-ios.sh`, `run-android.sh`, `run.sh`, `run-ios-device.sh`.
///
/// OAuth / deep link :
/// doit **matcher** `CFBundleURLSchemes` (iOS) et l’intent `android:scheme` (Android),
/// ainsi que les URI autorisées côté **dashboard Privy** pour le flux `privy.oAuth.login`.
/// Surcharge : `--dart-define=PRIVY_OAUTH_SCHEME=...` (sinon défaut `vancelian`).
class PrivyDartDefines {
  PrivyDartDefines._();

  static const String appId = String.fromEnvironment(
    'PRIVY_APP_ID',
    defaultValue: '',
  );

  static const String appClientId = String.fromEnvironment(
    'PRIVY_APP_CLIENT_ID',
    defaultValue: '',
  );

  /// Scheme du callback après OAuth Privy (`appUrlScheme` côté SDK).
  /// Défaut `vancelian` — doit être déclaré en natif (Info.plist / AndroidManifest).
  static const String oauthRedirectScheme = String.fromEnvironment(
    'PRIVY_OAUTH_SCHEME',
    defaultValue: 'vancelian',
  );

  static bool get isConfigured =>
      appId.trim().isNotEmpty && appClientId.trim().isNotEmpty;

  static bool get isOAuthRedirectConfigured =>
      oauthRedirectScheme.trim().isNotEmpty;
}
