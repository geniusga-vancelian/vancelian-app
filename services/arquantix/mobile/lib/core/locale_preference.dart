import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;

import 'config.dart';

/// Locale d’affichage active de l’app + locales activées côté admin.
///
/// - **Source de vérité runtime** pour les appels API mobile (`?locale=…`),
///   pour `MaterialApp.locale`, et pour le sélecteur du profil.
/// - **Persistance** : surchage utilisateur enregistrée via
///   `flutter_secure_storage` (clé non sensible mais on évite une dépendance
///   supplémentaire à `shared_preferences`).
/// - **Bootstrap** : `loadFromServer()` interroge `/api/site/i18n-policy` pour
///   récupérer `defaultLocale` + `supportedLocales` côté admin (mêmes que la
///   page Translation Settings du CMS).
///
/// Locale canonique de l’app **après bascule EN-first** : `'en'` (alignée sur
/// `defaultLocale = 'en'` côté Next.js et sur la langue source des copies CMS).
class LocalePreference extends ChangeNotifier {
  LocalePreference._();
  static final LocalePreference instance = LocalePreference._();

  /// Locale par défaut tant que la politique admin n’est pas chargée.
  /// Volontairement `'en'` (langue source / canonique).
  static const String fallbackLocale = 'en';

  static const _storageKey = 'arquantix.locale_override';
  static const _secure = FlutterSecureStorage();

  String _locale = fallbackLocale;
  String _defaultLocale = fallbackLocale;
  List<String> _supportedLocales = const <String>[fallbackLocale];
  bool _hasUserOverride = false;
  bool _multilingual = true;
  bool _loaded = false;

  /// Locale active utilisée par tous les appels API et `MaterialApp`.
  String get locale => _locale;

  /// Locale canonique côté admin (Translation Settings → Default language).
  String get defaultLocale => _defaultLocale;

  /// Locales activées dans `Site languages → Enabled locales` (admin).
  List<String> get supportedLocales => List.unmodifiable(_supportedLocales);

  /// Switch global multilingue activé côté admin (sinon : 1 seule locale).
  bool get multilingual => _multilingual;

  /// True quand l’utilisateur a explicitement choisi une langue via le profil.
  bool get hasUserOverride => _hasUserOverride;

  bool get isLoaded => _loaded;

  /// `Locale(_locale)` pour `MaterialApp.locale` ; renvoie `null` tant qu’aucun
  /// chargement/override n’a eu lieu (laisse Flutter faire son resolution
  /// callback).
  Locale? get materialLocale => _loaded || _hasUserOverride ? Locale(_locale) : null;

  /// À appeler **une fois** avant `runApp` (ou au plus tôt) :
  /// - lit l’override utilisateur (secure storage)
  /// - recharge la politique admin depuis `/api/site/i18n-policy`
  ///   (best-effort, silencieux si offline).
  Future<void> bootstrap() async {
    final stored = await _readStoredLocale();
    if (stored != null && stored.isNotEmpty) {
      _locale = stored;
      _hasUserOverride = true;
    }
    await loadFromServer();
    _loaded = true;
    notifyListeners();
  }

  /// Récupère la politique i18n publique (sans auth) et met à jour
  /// `defaultLocale` + `supportedLocales`. Si l’utilisateur n’a pas surchargé,
  /// aligne `locale` sur `defaultLocale` admin.
  Future<void> loadFromServer() async {
    try {
      final res = await http
          .get(Uri.parse(Config.i18nPolicyUrl))
          .timeout(const Duration(seconds: 5));
      if (res.statusCode != 200) return;
      final json = jsonDecode(res.body);
      if (json is! Map) return;
      final supported = (json['supportedLocales'] as List?)
              ?.map((e) => e.toString().trim())
              .where((s) => s.isNotEmpty)
              .toList(growable: false) ??
          const <String>[];
      final def = (json['defaultLocale']?.toString() ?? '').trim();
      _multilingual = json['multilingual'] != false;
      if (supported.isNotEmpty) _supportedLocales = supported;
      if (def.isNotEmpty) _defaultLocale = def;
      if (!_hasUserOverride && def.isNotEmpty) {
        _locale = def;
      } else if (_hasUserOverride && !_supportedLocales.contains(_locale)) {
        // L’admin a désactivé la locale choisie : retour au défaut.
        _locale = _defaultLocale;
        _hasUserOverride = false;
        await _secure.delete(key: _storageKey);
      }
      notifyListeners();
    } catch (e) {
      if (kDebugMode) debugPrint('LocalePreference.loadFromServer error: $e');
    }
  }

  /// Surcharge utilisateur depuis le sélecteur du profil.
  Future<void> setLocale(String code) async {
    final next = code.trim();
    if (next.isEmpty || next == _locale) return;
    _locale = next;
    _hasUserOverride = true;
    notifyListeners();
    try {
      await _secure.write(key: _storageKey, value: next);
    } catch (e) {
      if (kDebugMode) debugPrint('LocalePreference.setLocale persist error: $e');
    }
  }

  /// Repli sur la locale admin par défaut (déconnexion / reset).
  Future<void> clearOverride() async {
    if (!_hasUserOverride && _locale == _defaultLocale) return;
    _locale = _defaultLocale;
    _hasUserOverride = false;
    notifyListeners();
    try {
      await _secure.delete(key: _storageKey);
    } catch (_) {}
  }

  /// Helper utilisé dans les services API : retourne `override ?? locale`.
  String resolve([String? requested]) {
    if (requested != null && requested.trim().isNotEmpty) return requested.trim();
    return _locale;
  }

  Future<String?> _readStoredLocale() async {
    try {
      return await _secure.read(key: _storageKey);
    } catch (e) {
      if (kDebugMode) debugPrint('LocalePreference.read error: $e');
      return null;
    }
  }
}
