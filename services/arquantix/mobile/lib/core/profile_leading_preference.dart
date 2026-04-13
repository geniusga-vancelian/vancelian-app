import 'package:flutter/foundation.dart';

/// Initiales affichées sur le leading « profil » (dashboard, marchés, offres).
/// Renseignées au bootstrap ; [notifyListeners] pour rafraîchir les écrans déjà montés.
class ProfileLeadingPreference extends ChangeNotifier {
  ProfileLeadingPreference._();
  static final ProfileLeadingPreference instance = ProfileLeadingPreference._();

  static const String _fallback = 'JA';

  String _initials = _fallback;
  String get initials => _initials;

  void loadFromBootstrapJson(Object? raw) {
    final next = normalize(raw);
    if (_initials != next) {
      _initials = next;
      notifyListeners();
    }
  }

  void resetForLogout() {
    if (_initials != _fallback) {
      _initials = _fallback;
      notifyListeners();
    }
  }

  static String normalize(Object? raw) {
    if (raw == null) return _fallback;
    final s = raw.toString().trim();
    if (s.isEmpty) return _fallback;
    final t = s.toUpperCase();
    if (t.length <= 2) return t;
    return t.substring(0, 2);
  }
}
