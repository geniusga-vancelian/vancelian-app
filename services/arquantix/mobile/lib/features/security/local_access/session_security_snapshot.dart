import 'dart:convert';

/// Contexte minimal pour la politique de relock / biométrie (JWT + horodatages locaux).
/// Ne remplace pas l’auth serveur : lecture optionnelle des claims et état UX local.
class SessionSecuritySnapshot {
  const SessionSecuritySnapshot({
    this.stepUpOtpRequired = false,
    this.trustLevel,
    this.lastAuthStrength,
    this.lastSensitiveActionAt,
    this.lastLocalUnlockAt,
    this.sessionTrustLevel,
    this.lastStepUpAtEpochSec,
    this.jwtRelockRequired = false,
    this.jwtBiometricHint = false,
    this.accountState,
    this.securityIncomplete = false,
  });

  /// Claim JWT `step_up_otp` (backend FastAPI).
  final bool stepUpOtpRequired;

  /// Claim JWT `dtrust` (niveau de confiance appareil, chaîne libre côté API).
  final String? trustLevel;

  /// Claim JWT `auth_str` (ex. passkey, otp, password).
  final String? lastAuthStrength;

  /// Dernière action sensible côté client (optionnel, [SessionService.touchSensitiveAction]).
  final DateTime? lastSensitiveActionAt;

  /// Dernier déverrouillage local réussi (PIN ou biométrie).
  final DateTime? lastLocalUnlockAt;

  /// Claim JWT `strust` (confiance de session, Session Intelligence).
  final String? sessionTrustLevel;

  /// Claim JWT `lstup` (unix sec, dernier step-up serveur si présent).
  final int? lastStepUpAtEpochSec;

  /// Claim JWT `relock` — relock local plus agressif.
  final bool jwtRelockRequired;

  /// Claim JWT `bio_req` — pousser biométrie / PIN local.
  final bool jwtBiometricHint;

  /// Claim JWT `acct_st` (ACTIVE / PARTIAL / …) — UX / analytics ; pas seule vérité sécurité.
  final String? accountState;

  /// Claim JWT `sec_inc` — setup sécurité incomplet côté serveur.
  final bool securityIncomplete;

  static Map<String, dynamic>? _decodeJwtPayload(String accessToken) {
    final parts = accessToken.split('.');
    if (parts.length != 3) return null;
    try {
      final normalized = base64Url.normalize(parts[1]);
      return json.decode(utf8.decode(base64Url.decode(normalized)))
          as Map<String, dynamic>;
    } catch (_) {
      return null;
    }
  }

  /// Extrait step-up / confiance / force d’auth depuis un access token JWT.
  static SessionSecuritySnapshot fromAccessTokenClaims(String accessToken) {
    final p = _decodeJwtPayload(accessToken);
    if (p == null) {
      return const SessionSecuritySnapshot();
    }
    final stepUp = p['step_up_otp'] == true;
    final dtrust = p['dtrust'];
    final authStr = p['auth_str'];
    final strust = p['strust'];
    int? lstup;
    final rawLst = p['lstup'];
    if (rawLst is int) {
      lstup = rawLst;
    } else if (rawLst is num) {
      lstup = rawLst.toInt();
    }
    final acct = p['acct_st'];
    final acctStr = acct is String && acct.isNotEmpty ? acct.trim() : null;
    return SessionSecuritySnapshot(
      stepUpOtpRequired: stepUp,
      trustLevel: dtrust is String && dtrust.isNotEmpty ? dtrust : null,
      lastAuthStrength: authStr is String && authStr.isNotEmpty ? authStr : null,
      sessionTrustLevel: strust is String && strust.isNotEmpty ? strust : null,
      lastStepUpAtEpochSec: lstup,
      jwtRelockRequired: p['relock'] == true,
      jwtBiometricHint: p['bio_req'] == true,
      accountState: acctStr,
      securityIncomplete: p['sec_inc'] == true,
    );
  }

  Map<String, dynamic> toPersistedClaimsJson() => {
        'step_up_otp': stepUpOtpRequired,
        if (trustLevel != null) 'dtrust': trustLevel,
        if (lastAuthStrength != null) 'auth_str': lastAuthStrength,
        if (sessionTrustLevel != null) 'strust': sessionTrustLevel,
        if (lastStepUpAtEpochSec != null) 'lstup': lastStepUpAtEpochSec,
        if (jwtRelockRequired) 'relock': true,
        if (jwtBiometricHint) 'bio_req': true,
        if (accountState != null && accountState!.isNotEmpty) 'acct_st': accountState,
        if (securityIncomplete) 'sec_inc': true,
      };

  static SessionSecuritySnapshot fromPersistedClaimsJson(
    String? raw, {
    DateTime? lastSensitiveActionAt,
    DateTime? lastLocalUnlockAt,
  }) {
    if (raw == null || raw.isEmpty) {
      return SessionSecuritySnapshot(
        lastSensitiveActionAt: lastSensitiveActionAt,
        lastLocalUnlockAt: lastLocalUnlockAt,
      );
    }
    try {
      final m = json.decode(raw) as Map<String, dynamic>;
      final rawLst = m['lstup'];
      int? lstup;
      if (rawLst is int) {
        lstup = rawLst;
      } else if (rawLst is num) {
        lstup = rawLst.toInt();
      }
      final ac = m['acct_st'];
      return SessionSecuritySnapshot(
        stepUpOtpRequired: m['step_up_otp'] == true,
        trustLevel: m['dtrust'] as String?,
        lastAuthStrength: m['auth_str'] as String?,
        lastSensitiveActionAt: lastSensitiveActionAt,
        lastLocalUnlockAt: lastLocalUnlockAt,
        sessionTrustLevel: m['strust'] as String?,
        lastStepUpAtEpochSec: lstup,
        jwtRelockRequired: m['relock'] == true,
        jwtBiometricHint: m['bio_req'] == true,
        accountState: ac is String && ac.toString().trim().isNotEmpty
            ? ac.toString().trim()
            : null,
        securityIncomplete: m['sec_inc'] == true,
      );
    } catch (_) {
      return SessionSecuritySnapshot(
        lastSensitiveActionAt: lastSensitiveActionAt,
        lastLocalUnlockAt: lastLocalUnlockAt,
      );
    }
  }

  /// Heuristique locale : session « à risque » pour un relock plus agressif.
  bool get isElevatedLocalRisk {
    if (jwtRelockRequired) return true;
    if (stepUpOtpRequired) return true;
    final t = trustLevel?.toLowerCase().trim();
    if (t == null || t.isEmpty) return false;
    const suspicious = {'new_device', 'low', 'unknown', 'untrusted', 'suspect'};
    if (suspicious.contains(t)) return true;
    final st = sessionTrustLevel?.toUpperCase().trim();
    if (st == 'LOW') return true;
    return false;
  }
}
