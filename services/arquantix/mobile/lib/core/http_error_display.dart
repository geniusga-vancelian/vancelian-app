import 'dart:convert';

/// Message utilisateur (anglais) quand la réponse n’est pas une API JSON fiable.
const String kContentTemporarilyUnavailable =
    'Content temporarily unavailable. Please try again.';

/// Réponse HTML, page d’erreur Next dev, ou script embarqué — à ne jamais afficher brut dans l’UI.
bool responseBodyLooksLikeNonJsonApi(String body) {
  final t = body.trim();
  if (t.isEmpty) return false;
  final lower = t.toLowerCase();
  if (t.startsWith('<') || lower.contains('<html')) return true;
  if (lower.contains('<pre>') && lower.contains('missing required error components')) {
    return true;
  }
  if (lower.contains('async function check') && lower.contains('location.reload')) {
    return true;
  }
  if (lower.contains('<script') && lower.contains('fetch(location.href)')) return true;
  return false;
}

/// Message pour l’UI : jamais de HTML/JS brut ; JSON API inchangé pour debug raisonnable.
String userFacingHttpErrorMessage(int statusCode, String rawBody, {int maxLength = 420}) {
  if (responseBodyLooksLikeNonJsonApi(rawBody)) {
    return kContentTemporarilyUnavailable;
  }
  return httpErrorBodyForDisplay(statusCode, rawBody, maxLength: maxLength);
}

/// Extrait un message lisible depuis le corps d'une réponse HTTP d'erreur
/// (API JSON maison, payload Next.js dev `/_error`, HTML, texte brut).
String httpErrorBodyForDisplay(int statusCode, String rawBody, {int maxLength = 420}) {
  final t = rawBody.trim();
  if (t.isEmpty) {
    return 'HTTP $statusCode — réponse vide';
  }

  try {
    final decoded = jsonDecode(t);
    if (decoded is Map<String, dynamic>) {
      final msg = decoded['message'];
      if (msg is String && msg.trim().isNotEmpty) {
        return _trim('HTTP $statusCode — ${msg.trim()}', maxLength);
      }
      final err = decoded['err'];
      if (err is Map<String, dynamic>) {
        final em = err['message'];
        if (em is String && em.trim().isNotEmpty) {
          return _trim('HTTP $statusCode — ${em.trim()}', maxLength);
        }
      }
      final errStr = decoded['error'];
      if (errStr is String && errStr.trim().isNotEmpty) {
        return _trim('HTTP $statusCode — ${errStr.trim()}', maxLength);
      }
    }
  } catch (_) {
    // Pas du JSON
  }

  var plain = t.replaceAll(RegExp(r'<[^>]*>'), ' ').replaceAll(RegExp(r'\s+'), ' ').trim();
  if (plain.isEmpty) {
    plain = t;
  }
  return _trim(plain, maxLength);
}

String _trim(String s, int maxLength) {
  if (s.length <= maxLength) return s;
  return '${s.substring(0, maxLength)}…';
}
