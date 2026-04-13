/// Logos crypto en SVG — **source de vérité** : fichiers `assets/crypto_svgs/{ticker}.svg`
/// (export Figma / zip, noms en minuscules).
///
/// Réimport : décompresser l’archive dans `assets/crypto_svgs/` ou utiliser
/// `tool/import_crypto_export_zip.py`.
///
/// Utiliser [cryptoInstrumentSvgAssetPath] pour résoudre le chemin à partir d’un
/// ticker brut (ex. `BTCUSDT` → `BTC`, alias `TRON` → `TRX`).
library;

const String _kCryptoSvgDir = 'assets/crypto_svgs';

/// Tickers présents dans l’export (noms de fichiers en majuscules).
const Set<String> _kBundledExportTickers = {
  'AAVE',
  'ADA',
  'AED',
  'AGLD',
  'AKTIO',
  'ALCX',
  'ALGO',
  'ALPINE',
  'AMP',
  'ANKR',
  'ANT',
  'APE',
  'ARB',
  'ASI',
  'ATOM',
  'AUDIO',
  'AVAX',
  'AXS',
  'BAL',
  'BAT',
  'BCH',
  'BNB',
  'BOND',
  'BTC',
  'BUSD',
  'CAKE',
  'CELO',
  'CHR',
  'CHZ',
  'CLV',
  'COMP',
  'CREAM',
  'CRV',
  'CVX',
  'DAI',
  'DENT',
  'DOGE',
  'DOT',
  'DYDX',
  'ENJ',
  'EOS',
  'ETC',
  'ETH',
  'EUR',
  'EURC',
  'EURPAR',
  'FET',
  'FIL',
  'FLUX',
  'FTM',
  'FTT',
  'FTX',
  'GRT',
  'HBAR',
  'IOST',
  'IOTEX',
  'JTO',
  'KAVA',
  'KNC',
  'KSM',
  'LINK',
  'LPT',
  'LRC',
  'LTC',
  'LUNC',
  'MANA',
  'MATIC',
  'MDX',
  'MKR',
  'NEAR',
  'NKN',
  'NMR',
  'NOT',
  'OCEAN',
  'OGN',
  'OM',
  'ONE',
  'OXT',
  'PAXG',
  'PEPE',
  'PERP',
  'QNT',
  'REEF',
  'REN',
  'RENDER',
  'REQ',
  'RLC',
  'RSR',
  'RUNE',
  'SAND',
  'SHIB',
  'SKL',
  'SKY',
  'SNX',
  'SOL',
  'SONIC',
  'SRM',
  'STORJ',
  'STX',
  'SUI',
  'SUSHI',
  'THETA',
  'TON',
  'TRX',
  'TUSD',
  'UMA',
  'UNI',
  'USDC',
  'USDT',
  'VNC',
  'WBTC',
  'WLD',
  'XEM',
  'XLM',
  'XRP',
  'XTZ',
  'YFI',
  'YFII',
  'YGG',
  'ZIL',
  'ZRX',
};

/// Variantes → ticker dont le fichier `.svg` existe dans l’export.
const Map<String, String> _kTickerAliases = {
  /// Réseau Tron : fichier `trx.svg`.
  'TRON': 'TRX',
  'POL': 'MATIC',
  /// Logo Terra : seul `lunc.svg` dans l’export.
  'LUNA': 'LUNC',
  /// Smart chain : pas de `bsc.svg` → logo Binance.
  'BSC': 'BNB',
};

/// Retire les suffixes de cotation courants (`BTCUSDT` → `BTC`).
String normalizeCryptoBaseTicker(String raw) {
  var u = raw.trim().toUpperCase();
  if (u.isEmpty) return u;
  const suffixes = ['USDT', 'USDC', 'BUSD', 'DAI', 'EUR', 'USD'];
  for (final s in suffixes) {
    if (u.length > s.length && u.endsWith(s)) {
      final b = u.substring(0, u.length - s.length);
      if (b.isNotEmpty) u = b;
      break;
    }
  }
  return u;
}

/// Chemin `assets/crypto_svgs/{ticker}.svg` ou `null` si absent de l’export.
String? cryptoInstrumentSvgAssetPath(String rawTicker) {
  var k = normalizeCryptoBaseTicker(rawTicker);
  if (k.isEmpty) return null;
  k = _kTickerAliases[k] ?? k;
  if (!_kBundledExportTickers.contains(k)) return null;
  return '$_kCryptoSvgDir/${k.toLowerCase()}.svg';
}
