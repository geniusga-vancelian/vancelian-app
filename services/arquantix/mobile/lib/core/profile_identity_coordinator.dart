import 'package:flutter/foundation.dart';

import '../features/profile/data/mobile_app_profile.dart';
import '../features/profile/data/mobile_profile_api.dart';
import '../features/profile/debug/mobile_app_profile_registration_debug.dart';
import '../features/security/passcode/data/session_service.dart';
import 'profile_leading_preference.dart';
import 'session_bearer_http.dart';
import 'session_identity_context.dart';

/// Charge le profil mobile **canonique** (`GET …/profile`, même pipeline que Mon compte)
/// et aligne [ProfileLeadingPreference] sur les initiales du client JWT.
///
/// À utiliser pour éviter trois logiques parallèles (bootstrap seul, écran Profil, Mon compte).
/// Les réponses async obsolètes (logout / changement de compte) sont ignorées via [SessionIdentityContext.epoch].
class ProfileIdentityCoordinator {
  ProfileIdentityCoordinator._();
  static final ProfileIdentityCoordinator instance = ProfileIdentityCoordinator._();

  static const MobileProfileApi _api = MobileProfileApi();

  /// Dernier profil chargé avec succès pour l’[SessionIdentityContext.epoch] courant.
  /// Permet à Mon compte d’afficher tout de suite les données déjà récupérées au Home.
  MobileAppProfile? _cachedProfile;
  int _cachedEpoch = -1;

  /// Profil mis en cache si [SessionIdentityContext.epoch] n’a pas changé depuis le dernier chargement.
  MobileAppProfile? get cachedProfile =>
      SessionIdentityContext.instance.epoch == _cachedEpoch ? _cachedProfile : null;

  void _storeCache(MobileAppProfile? profile, int epoch) {
    _cachedEpoch = epoch;
    _cachedProfile = profile;
  }

  /// Profil Mon compte : réutilise le cache après [refreshDisplayIdentity] (ex. Home) si [forceRefresh] est false.
  Future<MobileAppProfile?> loadAccountProfile({
    bool forceRefresh = false,
    String debugTag = 'ProfileIdentityCoordinator.loadAccountProfile',
  }) async {
    final epoch = SessionIdentityContext.instance.epoch;
    if (!forceRefresh && _cachedEpoch == epoch && _cachedProfile != null) {
      if (kDebugMode) {
        debugPrint('[$debugTag] cache hit (epoch=$epoch)');
      }
      return _cachedProfile;
    }
    final p = await refreshDisplayIdentity(debugTag: debugTag);
    return p;
  }

  /// Rafraîchit initiales navbar + retourne le profil si succès.
  ///
  /// Sans jeton lisible : pas d’appel (retourne `null`).
  Future<MobileAppProfile?> refreshDisplayIdentity({
    String debugTag = 'ProfileIdentityCoordinator',
  }) async {
    final epoch = SessionIdentityContext.instance.epoch;
    final token = await SessionService.instance.readAccessToken();
    if (token == null || token.trim().isEmpty) {
      if (kDebugMode) {
        debugPrint('[$debugTag] skip: no access token');
      }
      _storeCache(null, epoch);
      return null;
    }

    MobileAppProfile? profile;
    try {
      profile = await _api.fetchProfile(accessToken: token);
    } on MissingBearerTokenException {
      if (kDebugMode) {
        debugPrint('[$debugTag] MissingBearerTokenException');
      }
      _storeCache(null, epoch);
      return null;
    }

    if (SessionIdentityContext.instance.epoch != epoch) {
      if (kDebugMode) {
        debugPrint('[$debugTag] discard: identity epoch changed (logout / switch user)');
      }
      return null;
    }

    if (profile != null) {
      ProfileLeadingPreference.instance.loadFromBootstrapJson(profile.initials);
      _storeCache(profile, epoch);
      debugLogMobileAppProfileRegistration(
        tag: debugTag,
        profile: profile,
        extra: 'après GET profile (initiales/nav + cache)',
      );
    } else {
      _storeCache(null, epoch);
      if (kDebugMode) {
        debugPrint(
          '[$debugTag] fetchProfile null — voir logs [MobileProfileApi] (HTTP ou parse)',
        );
        debugLogMobileAppProfileRegistration(
          tag: debugTag,
          profile: null,
          extra: 'fetchProfile null',
        );
      }
    }
    return profile;
  }
}
