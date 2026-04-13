import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import 'config.dart';

enum ReferenceCurrency {
  eur,
  usd;

  String get code => name.toUpperCase();
  String get symbol => this == eur ? '€' : '\$';
  String get label => code;

  static ReferenceCurrency fromCode(String? code) {
    if (code == null) return eur;
    switch (code.toUpperCase()) {
      case 'USD':
        return usd;
      default:
        return eur;
    }
  }
}

/// Singleton managing the user's reference currency preference.
///
/// Loaded from bootstrap, updated via PATCH.
/// Screens call [CurrencyPreference.instance] to read the current currency
/// and [addListener]/[removeListener] to react to changes.
class CurrencyPreference extends ChangeNotifier {
  CurrencyPreference._();
  static final CurrencyPreference instance = CurrencyPreference._();

  ReferenceCurrency _currency = ReferenceCurrency.eur;
  ReferenceCurrency get currency => _currency;

  /// Called once at bootstrap with the server value.
  void loadFromBootstrap(String? code) {
    _currency = ReferenceCurrency.fromCode(code);
  }

  /// Déconnexion ou changement de compte : évite d’afficher la devise du compte précédent.
  void resetForLogout() {
    _currency = ReferenceCurrency.eur;
    notifyListeners();
  }

  /// Persist to backend then update local state.
  Future<bool> update(ReferenceCurrency value) async {
    try {
      final url = Uri.parse(Config.referenceCurrencyUrl);
      final res = await http.patch(
        url,
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'reference_currency': value.code}),
      );
      if (res.statusCode == 200) {
        _currency = value;
        notifyListeners();
        return true;
      }
      return false;
    } catch (e) {
      debugPrint('CurrencyPreference.update error: $e');
      return false;
    }
  }

  /// Select the right value from a dual-currency payload.
  /// Returns EUR value when preference is EUR, USD value otherwise.
  /// Falls back to the available value if the preferred one is null.
  double? selectValue({double? eur, double? usd}) {
    if (_currency == ReferenceCurrency.eur) return eur ?? usd;
    return usd ?? eur;
  }

  /// Select a string value from dual-currency fields.
  String? selectString({String? eur, String? usd}) {
    if (_currency == ReferenceCurrency.eur) return eur ?? usd;
    return usd ?? eur;
  }
}
