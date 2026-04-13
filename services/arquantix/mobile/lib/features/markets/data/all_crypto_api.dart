import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../core/config.dart';
import '../../../core/currency_preference.dart';
import '../../../core/session_bearer_http.dart';

class AllCryptoApiException implements Exception {
  AllCryptoApiException(this.statusCode, this.message);

  final int statusCode;
  final String message;

  @override
  String toString() => 'AllCryptoApiException($statusCode): $message';
}

class AllCryptoItem {
  const AllCryptoItem({
    required this.slug,
    required this.name,
    required this.ticker,
    required this.price,
    this.priceEur,
    this.priceUsd,
    required this.variationPercent,
    required this.marketCapRank,
    required this.redirectUrl,
    this.providerSymbol,
    this.logoUrl,
  });

  final String slug;
  final String name;
  final String ticker;
  /// Formatted display price (in the current reference currency).
  final String price;
  /// Raw EUR price for currency switching.
  final double? priceEur;
  /// Raw USD/USDT price for currency switching.
  final double? priceUsd;
  final double variationPercent;
  final int marketCapRank;
  final String redirectUrl;
  final String? providerSymbol;
  final String? logoUrl;

  AllCryptoItem copyWith({String? price}) => AllCryptoItem(
        slug: slug,
        name: name,
        ticker: ticker,
        price: price ?? this.price,
        priceEur: priceEur,
        priceUsd: priceUsd,
        variationPercent: variationPercent,
        marketCapRank: marketCapRank,
        redirectUrl: redirectUrl,
        providerSymbol: providerSymbol,
        logoUrl: logoUrl,
      );
}

class AllCryptoApi {
  /// Charge l’ensemble des cryptos en base via l’API market-data (all-crypto).
  /// Avec session : envoie le Bearer (même résolution d’identité que les flux d’achat).
  Future<List<AllCryptoItem>> getAllCryptos({String locale = 'fr'}) async {
    final uri = Uri.parse(Config.allCryptoUrl);
    final response = await http.get(
      uri,
      headers: await SessionBearerHttp.jsonHeadersAppScoped(
        uri: uri,
        debugTag: 'AllCryptoApi.getAllCryptos',
      ),
    );
    if (response.statusCode != 200) {
      throw AllCryptoApiException(
        response.statusCode,
        response.body.isNotEmpty ? response.body : 'Erreur réseau',
      );
    }

    final json = jsonDecode(response.body) as Map<String, dynamic>;
    final raw = json['summaries'];
    if (raw is! List) return const [];
    final tickerFromProvider = (String? providerSymbol) {
      if (providerSymbol == null || providerSymbol.isEmpty) return '---';
      final s = providerSymbol.trim().toUpperCase();
      if (s == 'USDTUSDT') return 'USDT';
      if (s.endsWith('USDT')) return s.substring(0, s.length - 4);
      return s;
    };
    final pref = CurrencyPreference.instance;
    final items = raw
        .whereType<Map<String, dynamic>>()
        .map((it) {
          final name = (it['name'] ?? it['symbol'] ?? '').toString().trim();
          final symbol = (it['symbol'] ?? '').toString().trim().toUpperCase();
          final providerSymbol = (it['provider_symbol'] ?? it['symbol'] ?? '').toString().trim().toUpperCase();
          final ticker = symbol.isNotEmpty ? symbol : tickerFromProvider(providerSymbol);
          final slug = ticker.toLowerCase();

          final rawPriceUsd = it['price'] is num ? (it['price'] as num).toDouble() : double.tryParse((it['price'] ?? '').toString());
          final rawPriceEur = it['price_eur'] is num ? (it['price_eur'] as num).toDouble() : double.tryParse((it['price_eur'] ?? '').toString());
          final displayPrice = pref.selectValue(eur: rawPriceEur, usd: rawPriceUsd);
          final price = displayPrice != null
              ? formatPrice(displayPrice, currency: pref.currency)
              : '-';

          final varRaw = it['change_24h_pct'];
          final variation = varRaw is num
              ? varRaw.toDouble()
              : double.tryParse((varRaw ?? '').toString().replaceAll(',', '.')) ?? 0.0;
          final rank = (it['market_cap_rank'] is num)
              ? (it['market_cap_rank'] as num).toInt()
              : int.tryParse((it['market_cap_rank'] ?? '').toString().trim()) ?? 9999;
          final redirectUrl = ticker != '---' ? 'crypto://$slug' : '';
          final logoUrlRaw = it['logo_url'];
          final logoUrl = logoUrlRaw is String && logoUrlRaw.isNotEmpty ? logoUrlRaw : null;
          return AllCryptoItem(
            slug: slug,
            name: name.isNotEmpty ? name : 'Crypto',
            ticker: ticker,
            price: price,
            priceEur: rawPriceEur,
            priceUsd: rawPriceUsd,
            variationPercent: variation,
            marketCapRank: rank,
            redirectUrl: redirectUrl,
            providerSymbol: providerSymbol.isNotEmpty ? providerSymbol : null,
            logoUrl: logoUrl,
          );
        })
        .toList(growable: false);

    final sorted = [...items]..sort((a, b) => a.marketCapRank.compareTo(b.marketCapRank));
    return sorted;
  }

  /// Format prix pour affichage (partagé avec les mises à jour WebSocket).
  static String formatPrice(double value, {ReferenceCurrency? currency}) {
    final sym = (currency ?? CurrencyPreference.instance.currency).symbol;
    if (value >= 1000) {
      return '${value.toStringAsFixed(0).replaceAllMapped(
            RegExp(r'(\d{1,3})(?=(\d{3})+(?!\d))'),
            (m) => '${m[1]} ',
          )} $sym';
    }
    if (value >= 1) return '${value.toStringAsFixed(2).replaceAll('.', ',')} $sym';
    if (value >= 0.01) return '${value.toStringAsFixed(2).replaceAll('.', ',')} $sym';
    return '${value.toStringAsFixed(4).replaceAll('.', ',')} $sym';
  }
}
