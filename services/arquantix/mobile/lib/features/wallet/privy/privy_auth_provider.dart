import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:privy_flutter/privy_flutter.dart';

import 'privy_dart_defines.dart';
import 'privy_safe_log.dart';
import 'privy_sdk_holder.dart';

/// Identifiant de compte Privy (sujet côté provider).
typedef PrivyUserId = String;

/// Adresse de wallet exposée par le SDK (EVM, etc.).
class PrivyWalletAddress {
  const PrivyWalletAddress({
    required this.address,
    required this.chainType,
    this.chainId,
    required this.walletType,
  });

  final String address;
  /// Ex. `evm` (attendu par `POST /auth/privy/exchange`).
  final String chainType;
  final int? chainId;
  /// Ex. `embedded`, `external`.
  final String walletType;

  /// Payload pour [PrivyIdentityBridgeService.exchangePrivyToken].
  Map<String, dynamic> toExchangeJson() {
    return <String, dynamic>{
      'address': address,
      'chain_type': chainType,
      if (chainId != null) 'chain_id': chainId,
      'wallet_type': walletType,
    };
  }
}

class PrivyAuthProviderException implements Exception {
  PrivyAuthProviderException(this.message);
  final String message;

  @override
  String toString() => message;
}

/// Erreurs iOS/Android / CFNetwork souvent **transitoires** (Wi‑Fi, debug wireless, coupure courte).
///
/// Cf. logs type `NSURLErrorDomain Code=-1005` sur `auth.privy.io/.../passwordless/authenticate`.
/// OTP invalide ou expiré (messages SDK Privy typiques).
bool isPrivyWrongCodeError(Object error) {
  final s = error.toString().toLowerCase();
  return s.contains('invalid_credentials') ||
      s.contains('invalid email and code combination') ||
      s.contains('invalid code') ||
      s.contains('code expired') ||
      (s.contains('expired') && s.contains('code'));
}

bool _looksLikeTransientPrivyNetworkError(Object error) {
  final s = error.toString().toLowerCase();
  final hasUrlError = s.contains('nsurlerrordomain');
  return hasUrlError && (s.contains('-1005') || s.contains('1005')) ||
      hasUrlError && (s.contains('-1001') || s.contains('1001')) ||
      s.contains('connection was lost') ||
      s.contains('network connection was lost') ||
      s.contains('software caused connection abort') ||
      s.contains('connection reset by peer') ||
      s.contains('timed out');
}

Future<void> _runPrivyWithNetworkRetries(
  Future<void> Function() run, {
  String debugLabel = 'privy_http',
}) async {
  const maxAttempts = 4;
  for (var attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      await run();
      return;
    } catch (e, st) {
      final transient = _looksLikeTransientPrivyNetworkError(e);
      if (!transient || attempt == maxAttempts) {
        Error.throwWithStackTrace(e, st);
      }
      final backoff = Duration(milliseconds: 400 * attempt);
      if (kDebugMode) {
        debugPrint(
          '[$debugLabel] réseau transitoire, nouvel essai ${attempt + 1}/'
          '$maxAttempts dans ${backoff.inMilliseconds} ms',
        );
      }
      await Future<void>.delayed(backoff);
    }
  }
}

/// Abstraction **SDK Privy** — OAuth (recommandé parcours produit), OTP email (écran labo).
///
/// **Ne pas** y placer le `PRIVY_APP_SECRET` : seuls `appId` / `appClientId` côté client.
abstract class PrivyAuthProvider {
  /// Connexion Privy via fournisseur OAuth (Google, Apple, …). Nécessite un
  /// `appUrlScheme` natif aligné avec [PrivyDartDefines.oauthRedirectScheme].
  Future<void> loginWithOAuth(OAuthProvider provider);

  /// Envoie un code OTP Privy à l’email (fournisseur **Email** activé dans le dashboard Privy).
  Future<void> sendPrivyEmailCode(String email);

  /// Valide le code OTP et ouvre la session SDK Privy (« login » Privy).
  Future<void> completePrivyEmailLogin({
    required String email,
    required String code,
  });

  /// Valide l’OTP e-mail selon l’état Privy : login si déconnecté, mise à jour si déjà connecté.
  Future<void> completePrivyEmailVerification({
    required String email,
    required String code,
  });

  /// Session SDK Privy active (wallet / OAuth / OTP précédent).
  Future<bool> isPrivySessionActive();

  /// E-mail déjà rattaché au compte Privy courant, ou `null` (ex. wallet seul).
  Future<String?> getPrimaryPrivyEmail();

  Future<void> logout();

  /// Jeton d’accès client à envoyer à `POST /auth/privy/exchange`.
  Future<String?> getAccessToken();

  /// Wallet principal (embedded Ethereum) si présent.
  Future<PrivyWalletAddress?> getPrimaryWallet();

  /// Crée un embedded wallet Ethereum si l’utilisateur n’en a pas.
  Future<void> createEmbeddedWalletIfNeeded();

  /// Signe et envoie une transaction EVM via le wallet embedded Privy.
  Future<String> sendEthereumTransaction({
    required int chainId,
    required String to,
    required String data,
    required String value,
    String? gasLimit,
  });

  /// DID / id utilisateur Privy si session active (sinon `null`, sans exception).
  Future<String?> getLinkedPrivyUserId();

  /// Libellé d’état du SDK (écran dev).
  Future<String> describePrivyAuthStateLabel();
}

/// Fallback si les `--dart-define` ne sont pas fournis (pas d’init native Privy).
class PrivyAuthProviderUnimplemented implements PrivyAuthProvider {
  @override
  Future<void> loginWithOAuth(OAuthProvider provider) async {
    throw UnimplementedError(
      'Configurer PRIVY_APP_ID et PRIVY_APP_CLIENT_ID (dart-define).',
    );
  }

  @override
  Future<void> completePrivyEmailLogin({
    required String email,
    required String code,
  }) async {
    throw UnimplementedError(
      'Configurer PRIVY_APP_ID et PRIVY_APP_CLIENT_ID (dart-define).',
    );
  }

  @override
  Future<void> completePrivyEmailVerification({
    required String email,
    required String code,
  }) async {
    throw UnimplementedError(
      'Configurer PRIVY_APP_ID et PRIVY_APP_CLIENT_ID (dart-define).',
    );
  }

  @override
  Future<bool> isPrivySessionActive() async => false;

  @override
  Future<String?> getPrimaryPrivyEmail() async => null;

  @override
  Future<void> createEmbeddedWalletIfNeeded() async {
    throw UnimplementedError(
      'Configurer PRIVY_APP_ID et PRIVY_APP_CLIENT_ID (dart-define).',
    );
  }

  @override
  Future<String> sendEthereumTransaction({
    required int chainId,
    required String to,
    required String data,
    required String value,
    String? gasLimit,
  }) async {
    throw UnimplementedError(
      'Configurer PRIVY_APP_ID et PRIVY_APP_CLIENT_ID (dart-define).',
    );
  }

  @override
  Future<String?> getAccessToken() async => null;

  @override
  Future<PrivyWalletAddress?> getPrimaryWallet() async => null;

  @override
  Future<void> sendPrivyEmailCode(String email) async {
    throw UnimplementedError(
      'Configurer PRIVY_APP_ID et PRIVY_APP_CLIENT_ID (dart-define).',
    );
  }

  @override
  Future<void> logout() async {}

  @override
  Future<String?> getLinkedPrivyUserId() async => null;

  @override
  Future<String> describePrivyAuthStateLabel() async => 'Unconfigured / SDK absent';
}

/// Implémentation [privy_flutter](https://pub.dev/packages/privy_flutter) officielle.
class PrivyFlutterAuthProvider implements PrivyAuthProvider {
  PrivyFlutterAuthProvider(this._privy);

  final Privy _privy;

  Future<PrivyUser> _requireUser() async {
    final state = await _privy.getAuthState();
    final u = state.user;
    if (u != null) return u;
    final u2 = await _privy.getUser();
    if (u2 != null) return u2;
    throw PrivyAuthProviderException(
      'Session Privy inactive — se connecter via OAuth ou OTP email Privy.',
    );
  }

  @override
  Future<void> loginWithOAuth(OAuthProvider provider) async {
    final scheme = PrivyDartDefines.oauthRedirectScheme.trim();
    if (scheme.isEmpty) {
      throw PrivyAuthProviderException(
        'PRIVY_OAUTH_SCHEME vide — définir un scheme (Info.plist / AndroidManifest).',
      );
    }
    final r = await _privy.oAuth.login(
      provider: provider,
      appUrlScheme: scheme,
    );
    switch (r) {
      case Success():
        if (kDebugMode) {
          debugPrint('[Privy] OAuth login succeeded (${provider.name})');
        }
        return;
      case Failure(:final error):
        throw PrivyAuthProviderException(error.message);
    }
  }

  @override
  Future<void> sendPrivyEmailCode(String email) async {
    final e = email.trim();
    if (e.isEmpty) {
      throw PrivyAuthProviderException('Email requis.');
    }
    await _runPrivyWithNetworkRetries(() async {
      final r = await _privy.email.sendCode(e);
      switch (r) {
        case Success():
          return;
        case Failure(:final error):
          throw PrivyAuthProviderException(error.message);
      }
    }, debugLabel: 'privy.email.sendCode');
  }

  @override
  Future<bool> isPrivySessionActive() async {
    final state = await _privy.getAuthState();
    return state is Authenticated || state is AuthenticatedUnverified;
  }

  @override
  Future<String?> getPrimaryPrivyEmail() async {
    try {
      final state = await _privy.getAuthState();
      PrivyUser? user;
      if (state is Authenticated) {
        user = state.user;
      } else {
        user = await _privy.getUser();
      }
      if (user == null) return null;
      for (final account in user.linkedAccounts) {
        if (account is EmailAccount) {
          final addr = account.emailAddress.trim();
          if (addr.isNotEmpty) return addr;
        }
      }
    } catch (e) {
      if (kDebugMode) {
        debugPrint('[Privy] getPrimaryPrivyEmail: $e');
      }
    }
    return null;
  }

  @override
  Future<void> completePrivyEmailLogin({
    required String email,
    required String code,
  }) async {
    final e = email.trim();
    final c = code.trim();
    if (e.isEmpty || c.isEmpty) {
      throw PrivyAuthProviderException('Email et code requis.');
    }
    await _runPrivyWithNetworkRetries(() async {
      final r = await _privy.email.loginWithCode(email: e, code: c);
      switch (r) {
        case Success():
          if (kDebugMode) {
            debugPrint('[Privy] email OTP login succeeded');
          }
          return;
        case Failure(:final error):
          throw PrivyAuthProviderException(error.message);
      }
    }, debugLabel: 'privy.email.loginWithCode');
  }

  @override
  Future<void> completePrivyEmailVerification({
    required String email,
    required String code,
  }) async {
    final e = email.trim();
    final c = code.trim();
    if (e.isEmpty || c.isEmpty) {
      throw PrivyAuthProviderException('Email et code requis.');
    }

    final hasSession = await isPrivySessionActive();
    final privyEmail = hasSession ? await getPrimaryPrivyEmail() : null;
    final hasPrivyEmail = privyEmail != null && privyEmail.isNotEmpty;

    if (kDebugMode) {
      debugPrint(
        '[Privy] completePrivyEmailVerification target=$e '
        'hasSession=$hasSession privyEmail=${privyEmail ?? '(none)'} '
        '→ ${hasSession ? (hasPrivyEmail ? 'updateWithCode' : 'linkWithCode') : 'loginWithCode'}',
      );
    }

    Future<void> runUpdate() => _runPrivyWithNetworkRetries(() async {
      final r = await _privy.email.updateWithCode(email: e, code: c);
      switch (r) {
        case Success():
          if (kDebugMode) debugPrint('[Privy] email OTP update succeeded');
          return;
        case Failure(:final error):
          throw PrivyAuthProviderException(error.message);
      }
    }, debugLabel: 'privy.email.updateWithCode');

    Future<void> runLink() => _runPrivyWithNetworkRetries(() async {
      final r = await _privy.email.linkWithCode(email: e, code: c);
      switch (r) {
        case Success():
          if (kDebugMode) debugPrint('[Privy] email OTP link succeeded');
          return;
        case Failure(:final error):
          throw PrivyAuthProviderException(error.message);
      }
    }, debugLabel: 'privy.email.linkWithCode');

    if (hasSession) {
      // Doc Privy : updateWithCode si e-mail déjà lié ; linkWithCode si wallet seul.
      if (hasPrivyEmail) {
        await runUpdate();
      } else {
        await runLink();
      }
      return;
    }

    try {
      await completePrivyEmailLogin(email: e, code: c);
    } on PrivyAuthProviderException catch (loginErr) {
      if (isPrivyWrongCodeError(loginErr)) rethrow;
      if (await isPrivySessionActive()) {
        final linked = await getPrimaryPrivyEmail();
        final hasLinked = linked != null && linked.isNotEmpty;
        if (kDebugMode) {
          debugPrint(
            '[Privy] loginWithCode refusé (session active), '
            'fallback ${hasLinked ? 'updateWithCode' : 'linkWithCode'}',
          );
        }
        if (hasLinked) {
          await runUpdate();
        } else {
          await runLink();
        }
        return;
      }
      rethrow;
    }
  }

  @override
  Future<void> logout() async {
    await _privy.logout();
  }

  @override
  Future<String?> getAccessToken() async {
    final user = await _requireUser();
    final r = await user.getAccessToken();
    switch (r) {
      case Success(:final value):
        privyLogTokenMeta('privy_access_token', value);
        return value;
      case Failure(:final error):
        throw PrivyAuthProviderException(error.message);
    }
  }

  @override
  Future<PrivyWalletAddress?> getPrimaryWallet() async {
    final user = await _requireUser();
    final list = user.embeddedEthereumWallets;
    if (list.isEmpty) return null;
    final w = list.first;
    final chainIdParsed = int.tryParse(w.chainId ?? '');
    return PrivyWalletAddress(
      address: w.address,
      chainType: 'evm',
      chainId: chainIdParsed,
      walletType: 'embedded',
    );
  }

  @override
  Future<void> createEmbeddedWalletIfNeeded() async {
    final user = await _requireUser();
    if (user.embeddedEthereumWallets.isNotEmpty) {
      return;
    }
    final r = await user.createEthereumWallet();
    switch (r) {
      case Success():
        final refresh = await user.refresh();
        switch (refresh) {
          case Success():
            return;
          case Failure(:final error):
            throw PrivyAuthProviderException(
              'Wallet créé mais refresh utilisateur échoué : ${error.message}',
            );
        }
      case Failure(:final error):
        throw PrivyAuthProviderException(error.message);
    }
  }

  @override
  Future<String> sendEthereumTransaction({
    required int chainId,
    required String to,
    required String data,
    required String value,
    String? gasLimit,
  }) async {
    final user = await _requireUser();
    if (user.embeddedEthereumWallets.isEmpty) {
      throw PrivyAuthProviderException('Wallet embedded Privy requis.');
    }
    final wallet = user.embeddedEthereumWallets.first;

    final payload = <String, dynamic>{
      'from': wallet.address,
      'to': to,
      'data': data,
      'value': _toHexQuantity(value),
      'chainId': '0x${chainId.toRadixString(16)}',
      if (gasLimit != null && gasLimit.trim().isNotEmpty)
        'gasLimit': _toHexQuantity(gasLimit),
    };

    final request = EthereumRpcRequest.ethSendTransaction(jsonEncode(payload));
    final result = await wallet.provider.request(request);
    return switch (result) {
      Success(:final value) => _normalizeTxHash(value.data),
      Failure(:final error) => throw PrivyAuthProviderException(error.message),
    };
  }

  String _toHexQuantity(String raw) {
    final text = raw.trim();
    if (text.startsWith('0x')) return text;
    final value = BigInt.tryParse(text);
    if (value == null) {
      throw PrivyAuthProviderException('Montant transaction invalide.');
    }
    return '0x${value.toRadixString(16)}';
  }

  String _normalizeTxHash(String hash) {
    final trimmed = hash.trim();
    if (trimmed.startsWith('0x')) return trimmed;
    return '0x$trimmed';
  }

  @override
  Future<String?> getLinkedPrivyUserId() async {
    final state = await _privy.getAuthState();
    final u = state.user ?? await _privy.getUser();
    return u?.id;
  }

  @override
  Future<String> describePrivyAuthStateLabel() async {
    final state = await _privy.getAuthState();
    return switch (state) {
      Authenticated() => 'Authenticated',
      Unauthenticated() => 'Unauthenticated',
      NotReady() => 'NotReady',
      AuthenticatedUnverified() => 'AuthenticatedUnverified',
    };
  }
}

/// Singleton applicatif — bascule sur [PrivyAuthProviderUnimplemented] si non configuré.
PrivyAuthProvider createPrivyAuthProvider() {
  if (!PrivyDartDefines.isConfigured) {
    return PrivyAuthProviderUnimplemented();
  }
  return PrivyFlutterAuthProvider(PrivySdkHolder.instance.privy);
}
