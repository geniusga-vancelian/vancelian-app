import 'package:intl/intl.dart';

import 'currency_preference.dart';

/// Centralized currency formatting for the trading UI.
///
/// Uses [CurrencyPreference] to resolve the user's reference currency
/// and formats values accordingly.
class CurrencyFormatter {
  CurrencyFormatter._();

  static final _fmtEur = NumberFormat.decimalPattern('fr_FR');
  static final _fmtUsd = NumberFormat.decimalPattern('en_US');

  /// Current user currency symbol (e.g. "€" or "$").
  static String get symbol => CurrencyPreference.instance.currency.symbol;

  /// Current user currency code (e.g. "EUR" or "USD").
  static String get code => CurrencyPreference.instance.currency.code;

  /// Whether the user's reference currency is EUR.
  static bool get isEur => CurrencyPreference.instance.currency == ReferenceCurrency.eur;

  /// Format a price value with the user's currency symbol appended.
  ///
  /// Examples: "84 250.50 $" or "84 250,50 €"
  static String price(double value) {
    return '${_rawPrice(value)} $symbol';
  }

  /// Format a price without symbol (for use where symbol is shown separately).
  static String priceRaw(double value) {
    return _rawPrice(value);
  }

  /// Format a fiat amount with the user's currency symbol appended.
  ///
  /// Examples: "100.00 €" or "100.00 $"
  static String fiat(double value) {
    final fmt = isEur ? _fmtEur : _fmtUsd;
    if (value >= 1) return '${fmt.format(value)} $symbol';
    return '${value.toStringAsFixed(2)} $symbol';
  }

  /// Format fiat amount without symbol.
  static String fiatRaw(double value) {
    final fmt = isEur ? _fmtEur : _fmtUsd;
    if (value >= 1) return fmt.format(value);
    return value.toStringAsFixed(2);
  }

  /// Label for fiat input fields (e.g. "Montant (EUR)").
  static String fiatLabel(String prefix) => '$prefix ($code)';

  /// Label for price input fields (e.g. "Prix cible (EUR)").
  static String priceLabel(String prefix) => '$prefix ($code)';

  static String _rawPrice(double value) {
    final fmt = isEur ? _fmtEur : _fmtUsd;
    if (value >= 1) return fmt.format(value);
    if (value >= 0.01) return value.toStringAsFixed(4);
    return value.toStringAsFixed(8);
  }

  // ---------------------------------------------------------------------------
  // USD-specific formatters for the trading / orders feature.
  // Market data prices are always denominated in USD/USDT.
  // ---------------------------------------------------------------------------

  static const usdSymbol = '\$';

  /// Format a market price in USD with "$" appended.
  static String priceUsd(double value) => '${_rawPriceUsd(value)} \$';

  /// Format a market price in USD without symbol.
  static String priceUsdRaw(double value) => _rawPriceUsd(value);

  /// Format a fiat amount explicitly in EUR with "€" appended.
  static String fiatEur(double value) {
    if (value >= 1) return '${_fmtEur.format(value)} €';
    return '${value.toStringAsFixed(2)} €';
  }

  /// Format a fiat amount explicitly in EUR without symbol.
  static String fiatEurRaw(double value) {
    if (value >= 1) return _fmtEur.format(value);
    return value.toStringAsFixed(2);
  }

  static String _rawPriceUsd(double value) {
    if (value >= 1) return _fmtUsd.format(value);
    if (value >= 0.01) return value.toStringAsFixed(4);
    return value.toStringAsFixed(8);
  }
}
