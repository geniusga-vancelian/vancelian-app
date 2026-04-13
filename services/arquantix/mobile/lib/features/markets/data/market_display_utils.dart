/// Mapper symbole provider (ex. BTCUSDT) → nom d’affichage et symbole court.
/// Limité aux paires courantes ; pas de moteur métadonnées complet.
String marketDisplayName(String providerSymbol) {
  final s = (providerSymbol).trim().toUpperCase();
  if (s.isEmpty) return 'Crypto';
  switch (s) {
    case 'BTCUSDT':
      return 'Bitcoin';
    case 'ETHUSDT':
      return 'Ether';
    case 'SOLUSDT':
      return 'Solana';
    case 'XRPUSDT':
      return 'XRP';
    case 'BNBUSDT':
      return 'BNB';
    case 'ADAUSDT':
      return 'Cardano';
    case 'DOGEUSDT':
      return 'Dogecoin';
    case 'USDCUSDT':
      return 'USD Coin';
    case 'USDTUSDT':
      return 'Tether';
    case 'AVAXUSDT':
      return 'Avalanche';
    case 'LINKUSDT':
      return 'Chainlink';
    case 'DOTUSDT':
      return 'Polkadot';
    default:
      // Retirer le suffixe USDT si présent pour afficher un nom court
      if (s.endsWith('USDT')) {
        return s.substring(0, s.length - 4);
      }
      return s;
  }
}

/// Symbole court pour affichage (ex. BTCUSDT → BTC).
String marketShortSymbol(String providerSymbol) {
  final s = (providerSymbol).trim().toUpperCase();
  if (s.isEmpty) return '—';
  if (s == 'USDTUSDT') return 'USDT';
  if (s.endsWith('USDT')) {
    return s.substring(0, s.length - 4);
  }
  return s;
}

/// Ticker court → symbole provider (ex. BTC → BTCUSDT). Pour appels API market-data.
String tickerToProviderSymbol(String ticker) {
  final t = (ticker).trim().toUpperCase();
  if (t.isEmpty) return 'BTCUSDT';
  if (t == 'USDT') return 'USDTUSDT';
  return '${t}USDT';
}

/// Symboles par défaut pour l’onglet « Populaires » (market-summary).
const List<String> defaultPopularSymbols = [
  'BTCUSDT',
  'ETHUSDT',
  'SOLUSDT',
  'XRPUSDT',
  'BNBUSDT',
  'ADAUSDT',
  'DOGEUSDT',
  'USDCUSDT',
];

/// Séparateur de milliers pour lisibilité (ex. 59 644).
String _formatWithSpaces(String s) {
  final buffer = StringBuffer();
  for (var i = 0; i < s.length; i++) {
    if (i > 0 && (s.length - i) % 3 == 0 && s[i - 1] != ' ') {
      buffer.write(' ');
    }
    buffer.write(s[i]);
  }
  return buffer.toString();
}

/// Formatage prix : 2 décimales pour grandes valeurs, plus pour petites.
/// Les grands nombres utilisent un espace comme séparateur de milliers.
/// No currency symbol appended — used when the symbol is added elsewhere.
String formatPrice(double value) {
  if (value >= 1000) {
    final intPart = value.truncate();
    final dec = value - intPart;
    final s = intPart.toString();
    final formatted = _formatWithSpaces(s);
    if (dec <= 0) return formatted;
    final decStr = dec.toStringAsFixed(2).replaceFirst('0', '');
    return '$formatted$decStr';
  }
  if (value >= 1) {
    return value.toStringAsFixed(2);
  }
  if (value >= 0.01) {
    return value.toStringAsFixed(4);
  }
  if (value >= 0.0001) {
    return value.toStringAsFixed(6);
  }
  return value.toStringAsFixed(8);
}

/// Formatage pourcentage avec signe ; 2 décimales.
String formatPercent(double? value) {
  if (value == null) return '—';
  final sign = value >= 0 ? '+' : '';
  return '$sign${value.toStringAsFixed(2)} %';
}

/// Formatage volume compact (K, M, B) optionnel.
String formatVolumeCompact(double value) {
  if (value >= 1e9) {
    return '${(value / 1e9).toStringAsFixed(1)}B';
  }
  if (value >= 1e6) {
    return '${(value / 1e6).toStringAsFixed(1)}M';
  }
  if (value >= 1e3) {
    return '${(value / 1e3).toStringAsFixed(1)}K';
  }
  return value.toStringAsFixed(0);
}
