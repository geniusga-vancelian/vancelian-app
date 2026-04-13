import 'passkey_platform_provider_factory_stub.dart'
    if (dart.library.io) 'passkey_platform_provider_factory_io.dart' as impl;
import 'passkey_provider.dart';

/// Fabrique d’implémentation [PasskeyPlatformProvider] (natif iOS/Android ou stub).
PasskeyPlatformProvider createPasskeyProvider() => impl.createPasskeyProvider();
