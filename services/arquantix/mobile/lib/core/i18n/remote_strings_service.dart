import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

import '../config.dart';
import '../locale_preference.dart';

/// Cache + résolveur runtime des **overrides UI strings** servis par le BFF
/// Next.js (`/api/mobile/flutter/ui-strings`).
///
/// Pattern aligné sur [LocalePreference] : singleton [ChangeNotifier], bootstrap
/// au démarrage, persistance via `flutter_secure_storage` (clé non sensible —
/// on évite simplement une dépendance supplémentaire).
///
/// **Sémantique d'override** : le service ne contient **que les overrides**
/// publiés côté admin (clés dont la valeur diffère du `sourceText` ARB). Toutes
/// les autres clés résolvent sur le fallback `AppLocalizations` compilé dans
/// le binaire. Conséquences :
///   - **Offline** : l'app fonctionne avec ARB compilé.
///   - **OTA** : les overrides apparaissent dès le prochain `refresh()`.
///   - **Coût réseau** : bundle minimal (souvent < 1 KB).
///
/// Le service s'auto-rafraîchit quand la locale change ([LocalePreference]
/// notifie → [reload] best-effort, silencieux si offline).
class RemoteStringsService extends ChangeNotifier {
  RemoteStringsService._();
  static final RemoteStringsService instance = RemoteStringsService._();

  static const _bundleStorageKey = 'arquantix.ui_strings.bundle.v1';
  static const _etagStorageKey = 'arquantix.ui_strings.etag.v1';
  static const _localeStorageKey = 'arquantix.ui_strings.locale.v1';
  static const _secure = FlutterSecureStorage();

  /// Backoff léger après un échec réseau, pour éviter de marteler le BFF.
  static const Duration _refreshThrottle = Duration(seconds: 30);

  Map<String, String> _overrides = const <String, String>{};
  String _bundleLocale = '';
  String? _etag;
  bool _loaded = false;
  DateTime _lastRefreshAttempt = DateTime.fromMillisecondsSinceEpoch(0);
  VoidCallback? _localeListener;

  /// Locale du bundle actuellement en mémoire (peut différer de la locale
  /// active si le serveur a appliqué un fallback).
  String get bundleLocale => _bundleLocale;

  /// True une fois le bootstrap terminé (lecture cache disque + 1 tentative
  /// de refresh réseau).
  bool get isLoaded => _loaded;

  /// Nombre d'overrides actifs (debug / observabilité).
  int get overridesCount => _overrides.length;

  /// Lookup direct : renvoie l'override pour [key] dans la locale du bundle
  /// courant, ou `null` si aucun override (l'appelant utilisera son fallback ARB).
  ///
  /// **Toujours appelé depuis [tr()]** dans le widget pour bénéficier du
  /// fallback typé. À ne pas appeler directement sauf cas particulier.
  String? lookup(String key) {
    if (!_loaded || _overrides.isEmpty) return null;
    return _overrides[key];
  }

  /// **À appeler une fois** avant `runApp` (typiquement via `_warmStartServices`).
  ///
  /// Étapes :
  ///   1. Restaure le bundle depuis le cache disque (instantané).
  ///   2. Hook sur [LocalePreference.instance] pour invalider le bundle quand
  ///      la locale change.
  ///   3. Tente un `refresh()` best-effort en arrière-plan.
  Future<void> bootstrap() async {
    await _restoreFromCache();
    final notifier = LocalePreference.instance;
    if (_localeListener != null) {
      notifier.removeListener(_localeListener!);
    }
    void onLocaleChanged() {
      if (notifier.locale != _bundleLocale) {
        unawaited(refresh());
      }
    }
    _localeListener = onLocaleChanged;
    notifier.addListener(onLocaleChanged);
    _loaded = true;
    notifyListeners();
    unawaited(refresh());
  }

  /// Force un refresh (best-effort). Respecte un throttle de 30 s pour ne pas
  /// spammer le BFF (sauf [force]=true).
  Future<void> refresh({bool force = false}) async {
    final now = DateTime.now();
    if (!force && now.difference(_lastRefreshAttempt) < _refreshThrottle) {
      return;
    }
    _lastRefreshAttempt = now;
    final locale = LocalePreference.instance.locale;
    final url = '${Config.uiStringsUrl}?locale=${Uri.encodeComponent(locale)}';
    try {
      final headers = <String, String>{
        if (_etag != null && _bundleLocale == locale) 'If-None-Match': _etag!,
      };
      final res = await http
          .get(Uri.parse(url), headers: headers)
          .timeout(const Duration(seconds: 6));

      if (res.statusCode == 304) {
        return;
      }
      if (res.statusCode != 200) {
        if (kDebugMode) {
          debugPrint('RemoteStringsService refresh non-200: ${res.statusCode}');
        }
        return;
      }
      final body = jsonDecode(res.body);
      if (body is! Map) return;
      final stringsRaw = body['strings'];
      if (stringsRaw is! Map) return;
      final next = <String, String>{};
      stringsRaw.forEach((k, v) {
        if (k is String && v is String) next[k] = v;
      });
      final responseLocale = (body['locale']?.toString() ?? locale).trim();
      final etag = res.headers['etag'];
      _overrides = Map.unmodifiable(next);
      _bundleLocale = responseLocale;
      _etag = etag;
      await _persist();
      notifyListeners();
    } catch (e) {
      if (kDebugMode) debugPrint('RemoteStringsService refresh error: $e');
    }
  }

  /// Réinitialise le service (utilisé en cas de reset/déconnexion). Vide le
  /// cache disque et la mémoire — l'app retombe sur les ARB compilés.
  Future<void> reset() async {
    _overrides = const <String, String>{};
    _bundleLocale = '';
    _etag = null;
    try {
      await _secure.delete(key: _bundleStorageKey);
      await _secure.delete(key: _etagStorageKey);
      await _secure.delete(key: _localeStorageKey);
    } catch (_) {}
    notifyListeners();
  }

  Future<void> _restoreFromCache() async {
    try {
      final raw = await _secure.read(key: _bundleStorageKey);
      final etag = await _secure.read(key: _etagStorageKey);
      final loc = await _secure.read(key: _localeStorageKey);
      if (raw != null && raw.isNotEmpty) {
        final decoded = jsonDecode(raw);
        if (decoded is Map) {
          final next = <String, String>{};
          decoded.forEach((k, v) {
            if (k is String && v is String) next[k] = v;
          });
          _overrides = Map.unmodifiable(next);
        }
      }
      _etag = etag;
      _bundleLocale = (loc ?? '').trim();
    } catch (e) {
      if (kDebugMode) debugPrint('RemoteStringsService restore error: $e');
    }
  }

  Future<void> _persist() async {
    try {
      await _secure.write(
        key: _bundleStorageKey,
        value: jsonEncode(_overrides),
      );
      if (_etag != null) {
        await _secure.write(key: _etagStorageKey, value: _etag!);
      }
      await _secure.write(key: _localeStorageKey, value: _bundleLocale);
    } catch (e) {
      if (kDebugMode) debugPrint('RemoteStringsService persist error: $e');
    }
  }
}
