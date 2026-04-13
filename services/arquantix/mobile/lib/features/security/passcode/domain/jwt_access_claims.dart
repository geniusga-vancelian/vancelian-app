import 'dart:convert';

/// `true` si la chaîne ressemble à un identifiant technique (UUID, hash hex long) — à ne pas
/// afficher comme prénom (le backend peut mettre l’ID client dans `name` par erreur).
bool jwtIsLikelyOpaqueUserIdentifier(String raw) {
  final s = raw.trim();
  if (s.isEmpty) return true;
  if (s.length > 48) return true;
  if (RegExp(
        r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$',
      ).hasMatch(s)) {
    return true;
  }
  if (s.length >= 24 && RegExp(r'^[a-fA-F0-9]+$').hasMatch(s)) return true;
  return false;
}

/// Lecture minimale des JWT access (évite les imports circulaires session ↔ stockage profil).
String? jwtExtractSubject(String accessToken) {
  final parts = accessToken.split('.');
  if (parts.length != 3) return null;
  try {
    final normalized = base64Url.normalize(parts[1]);
    final payload =
        json.decode(utf8.decode(base64Url.decode(normalized)))
            as Map<String, dynamic>;
    final sub = payload['sub'];
    if (sub is String) {
      final t = sub.trim();
      if (t.isNotEmpty) return t;
    }
  } catch (_) {}
  return null;
}

/// `person_id` / `pid` (profil portfolio), si présents dans le JWT.
String? jwtExtractPersonId(String accessToken) {
  final parts = accessToken.split('.');
  if (parts.length != 3) return null;
  try {
    final normalized = base64Url.normalize(parts[1]);
    final payload =
        json.decode(utf8.decode(base64Url.decode(normalized)))
            as Map<String, dynamic>;
    final raw = payload['person_id'] ?? payload['pid'];
    if (raw is String) {
      final t = raw.trim();
      if (t.isNotEmpty) return t;
    }
  } catch (_) {}
  return null;
}

/// Claim optionnel `client_id` / `cid` — si le backend l’ajoute, doit matcher le client résolu.
/// Date d’expiration du access token (`exp`, secondes Unix) → ms depuis epoch, ou null.
int? jwtExtractExpiryMs(String accessToken) {
  final parts = accessToken.split('.');
  if (parts.length != 3) return null;
  try {
    final normalized = base64Url.normalize(parts[1]);
    final payload =
        json.decode(utf8.decode(base64Url.decode(normalized)))
            as Map<String, dynamic>;
    final exp = payload['exp'];
    if (exp is int) return exp * 1000;
    if (exp is num) return (exp * 1000).round();
  } catch (_) {}
  return null;
}

/// Claim ``acct_st`` (état compte app : ACTIVE, PARTIAL, …).
String? jwtExtractAccountState(String accessToken) {
  final parts = accessToken.split('.');
  if (parts.length != 3) return null;
  try {
    final normalized = base64Url.normalize(parts[1]);
    final payload =
        json.decode(utf8.decode(base64Url.decode(normalized)))
            as Map<String, dynamic>;
    final raw = payload['acct_st'];
    if (raw is String) {
      final t = raw.trim();
      if (t.isNotEmpty) return t;
    }
  } catch (_) {}
  return null;
}

/// ``true`` si le JWT indique une session incomplète (passcode serveur / setup requis).
bool jwtExtractSecurityIncomplete(String accessToken) {
  final parts = accessToken.split('.');
  if (parts.length != 3) return false;
  try {
    final normalized = base64Url.normalize(parts[1]);
    final payload =
        json.decode(utf8.decode(base64Url.decode(normalized)))
            as Map<String, dynamic>;
    return payload['sec_inc'] == true;
  } catch (_) {}
  return false;
}

/// Accès « compte app complet » : **ACTIVE** sans ``sec_inc``. Les JWT sans ``acct_st`` sont traités comme legacy (actifs si pas ``sec_inc``).
bool isAccessTokenAccountActiveForApp(String accessToken) {
  if (jwtExtractSecurityIncomplete(accessToken)) return false;
  final st = jwtExtractAccountState(accessToken);
  if (st == null || st.isEmpty) return true;
  return st == 'ACTIVE';
}

String? jwtExtractOptionalClientIdClaim(String accessToken) {
  final parts = accessToken.split('.');
  if (parts.length != 3) return null;
  try {
    final normalized = base64Url.normalize(parts[1]);
    final payload =
        json.decode(utf8.decode(base64Url.decode(normalized)))
            as Map<String, dynamic>;
    final raw = payload['client_id'] ?? payload['cid'];
    if (raw is String) {
      final t = raw.trim();
      if (t.isNotEmpty) return t;
    }
  } catch (_) {}
  return null;
}

/// Prénom pour l’accueil : claims JWT classiques, sinon partie locale de `sub` si e-mail.
String? jwtExtractGreetingFirstName(String accessToken) {
  final parts = accessToken.split('.');
  if (parts.length != 3) return null;
  try {
    final normalized = base64Url.normalize(parts[1]);
    final payload =
        json.decode(utf8.decode(base64Url.decode(normalized)))
            as Map<String, dynamic>;
    final sub = payload['sub'];
    final subStr = sub is String ? sub.trim() : null;

    bool okCandidate(String t) {
      if (t.isEmpty) return false;
      if (jwtIsLikelyOpaqueUserIdentifier(t)) return false;
      if (subStr != null && subStr.isNotEmpty && t == subStr) return false;
      return true;
    }

    for (final key in ['given_name', 'first_name', 'firstname']) {
      final v = payload[key];
      if (v is String) {
        final t = v.trim();
        if (okCandidate(t)) return t;
      }
    }
    final name = payload['name'];
    if (name is String) {
      final t = name.trim();
      if (t.isNotEmpty) {
        final first = t.split(RegExp(r'\s+')).first;
        if (okCandidate(first)) return first;
      }
    }
  } catch (_) {}
  return _firstNameFromEmailLikeSub(jwtExtractSubject(accessToken));
}

String? _firstNameFromEmailLikeSub(String? sub) {
  if (sub == null || sub.isEmpty || !sub.contains('@')) return null;
  final local = sub.split('@').first.trim().toLowerCase();
  if (local.isEmpty) return null;
  final chunk = local.split(RegExp(r'[._+\-]')).firstWhere(
        (s) => s.isNotEmpty,
        orElse: () => '',
      );
  if (chunk.length < 2) return null;
  if (RegExp(r'^\d+$').hasMatch(chunk)) return null;
  return chunk[0].toUpperCase() + chunk.substring(1);
}
