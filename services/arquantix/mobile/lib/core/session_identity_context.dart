import 'package:flutter/foundation.dart';

import '../features/security/passcode/data/session_service.dart';
import '../features/security/passcode/domain/jwt_access_claims.dart';

/// Source de vérité locale pour l’identité de session (mobile) : alignée sur le JWT
/// et enrichie par le bootstrap (`client.id`).
///
/// Toute navigation « post-login » doit d’abord passer par [SessionService.storeTokens],
/// qui synchronise ce contexte. Le dashboard appelle [waitForAccessTokenForDashboard]
/// pour éviter les courses token / requêtes.
class SessionIdentityContext {
  SessionIdentityContext._();
  static final SessionIdentityContext instance = SessionIdentityContext._();

  /// Incrémenté à chaque [clear] — permet d’ignorer des réponses async obsolètes.
  int _epoch = 0;
  int get epoch => _epoch;

  String? _jwtSubject;
  String? _personId;
  String? _resolvedClientId;
  String? _lastOptionalClientIdClaim;

  String? get jwtSubject => _jwtSubject;
  String? get personId => _personId;
  String? get resolvedClientId => _resolvedClientId;

  /// Session authentifiée avec au moins un jeton et claims de base issus du JWT.
  bool get isHydratedFromToken =>
      _jwtSubject != null &&
      _jwtSubject!.isNotEmpty;

  /// Après bootstrap réussi, on attend un `client.id` cohérent avec la session.
  bool get isReadyForDashboard =>
      isHydratedFromToken &&
      _resolvedClientId != null &&
      _resolvedClientId!.isNotEmpty;

  /// À appeler après écriture des jetons (login, refresh) — jamais de client par défaut ici.
  void syncFromAccessToken(String accessToken) {
    _jwtSubject = jwtExtractSubject(accessToken);
    _personId = jwtExtractPersonId(accessToken);
    _lastOptionalClientIdClaim = jwtExtractOptionalClientIdClaim(accessToken);
  }

  /// Enrichissement depuis `GET .../bootstrap` (`client` JSON).
  void hydrateResolvedClientIdFromBootstrap(String clientId) {
    final cid = clientId.trim();
    if (cid.isEmpty) return;

    final claim = _lastOptionalClientIdClaim;
    if (claim != null && claim.isNotEmpty && claim != cid) {
      debugPrint(
        '[SessionIdentity] bootstrap client id != optional JWT client_id/cid claim '
        '(resolved=$cid claim=$claim)',
      );
    }
    _resolvedClientId = cid;
  }

  /// Déconnexion ou révocation : tout invalider.
  void clear() {
    _epoch++;
    _jwtSubject = null;
    _personId = null;
    _resolvedClientId = null;
    _lastOptionalClientIdClaim = null;
  }

  /// Attend qu’un access token soit lisible (course login → navigation → [HomeScreen]).
  /// Retourne le jeton pour enchaîner les appels API uniquement après preuve locale du Bearer.
  Future<String?> waitForAccessTokenForDashboard({
    Duration timeout = const Duration(seconds: 8),
  }) async {
    final deadline = DateTime.now().add(timeout);
    while (DateTime.now().isBefore(deadline)) {
      final t = await SessionService.instance.readAccessToken();
      if (t != null && t.isNotEmpty) {
        syncFromAccessToken(t);
        return t;
      }
      await Future<void>.delayed(const Duration(milliseconds: 40));
    }
    return null;
  }

  Future<bool> ensureAccessTokenReadyForDashboard({
    Duration timeout = const Duration(seconds: 8),
  }) async {
    final t = await waitForAccessTokenForDashboard(timeout: timeout);
    return t != null;
  }
}
