import 'package:flutter/foundation.dart';
import 'package:privy_flutter/privy_flutter.dart';

import 'privy_dart_defines.dart';

/// Instance unique [Privy] — requis par la doc Privy.
class PrivySdkHolder {
  PrivySdkHolder._();
  static final PrivySdkHolder instance = PrivySdkHolder._();

  Privy? _privy;

  Privy get privy {
    if (!PrivyDartDefines.isConfigured) {
      throw StateError(
        'Privy non configuré : fournir --dart-define=PRIVY_APP_ID et PRIVY_APP_CLIENT_ID',
      );
    }
    _privy ??= Privy.init(
      config: PrivyConfig(
        appId: PrivyDartDefines.appId.trim(),
        appClientId: PrivyDartDefines.appClientId.trim(),
        logLevel: kDebugMode ? PrivyLogLevel.verbose : PrivyLogLevel.none,
      ),
    );
    return _privy!;
  }
}
