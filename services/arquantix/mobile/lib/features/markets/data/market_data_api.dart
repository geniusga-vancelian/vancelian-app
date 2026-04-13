import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../../../core/config.dart';
import '../../../core/session_bearer_http.dart';

/// Exception levée par [MarketDataApi].
class MarketDataApiException implements Exception {
  MarketDataApiException(this.statusCode, this.message);

  final int statusCode;
  final String message;

  @override
  String toString() => 'MarketDataApiException($statusCode): $message';
}

/// Un item de market-summary ou top-movers (structure commune backend).
class MarketSummaryItem {
  const MarketSummaryItem({
    required this.instrumentId,
    required this.symbol,
    required this.price,
    this.priceEur,
    this.change24hAbs,
    this.change24hPct,
    this.volume24h = 0.0,
    this.sparkline24h = const [],
    this.logoUrl,
  });

  final int instrumentId;
  final String symbol;
  /// Raw price in USDT (treated as USD).
  final double price;
  /// Price converted to EUR by backend.
  final double? priceEur;
  final double? change24hAbs;
  final double? change24hPct;
  final double volume24h;
  final List<double> sparkline24h;
  /// URL du logo crypto (servi par le backend /media/crypto_logos/...).
  final String? logoUrl;

  static MarketSummaryItem fromJson(Map<String, dynamic> json) {
    final rawPrice = json['price'];
    final price = rawPrice is num
        ? rawPrice.toDouble()
        : double.tryParse(rawPrice?.toString() ?? '') ?? 0.0;
    final rawPriceEur = json['price_eur'];
    final priceEur = rawPriceEur is num
        ? rawPriceEur.toDouble()
        : double.tryParse(rawPriceEur?.toString() ?? '');
    final rawChangePct = json['change_24h_pct'];
    final change24hPct = rawChangePct is num
        ? rawChangePct.toDouble()
        : double.tryParse(rawChangePct?.toString() ?? '');
    final rawChangeAbs = json['change_24h_abs'];
    final change24hAbs = rawChangeAbs is num
        ? rawChangeAbs.toDouble()
        : double.tryParse(rawChangeAbs?.toString() ?? '');
    final rawVol = json['volume_24h'];
    final volume24h = rawVol is num
        ? rawVol.toDouble()
        : double.tryParse(rawVol?.toString() ?? '') ?? 0.0;
    final rawSpark = json['sparkline_24h'];
    List<double> sparkline24h = const [];
    if (rawSpark is List) {
      sparkline24h = rawSpark
          .map((e) => e is num ? e.toDouble() : double.tryParse(e?.toString() ?? '') ?? 0.0)
          .where((e) => e > 0)
          .toList();
    }
    final logoUrlRaw = json['logo_url'];
    final logoUrl = logoUrlRaw is String && logoUrlRaw.toString().trim().isNotEmpty
        ? logoUrlRaw.toString().trim()
        : null;
    return MarketSummaryItem(
      instrumentId: json['instrument_id'] is int
          ? json['instrument_id'] as int
          : int.tryParse(json['instrument_id']?.toString() ?? '') ?? 0,
      symbol: (json['symbol'] ?? '').toString().trim().toUpperCase(),
      price: price,
      priceEur: priceEur,
      change24hAbs: change24hAbs,
      change24hPct: change24hPct,
      volume24h: volume24h,
      sparkline24h: sparkline24h,
      logoUrl: logoUrl,
    );
  }
}

/// Réponse top-movers : top_gainers, top_losers (listes de résumés).
class TopMoversResponse {
  const TopMoversResponse({
    this.topGainers = const [],
    this.topLosers = const [],
  });

  final List<MarketSummaryItem> topGainers;
  final List<MarketSummaryItem> topLosers;

  static TopMoversResponse fromJson(Map<String, dynamic> json) {
    List<MarketSummaryItem> listFrom(List<dynamic>? raw) {
      if (raw == null) return [];
      return raw
          .whereType<Map<String, dynamic>>()
          .map((e) => MarketSummaryItem.fromJson(e))
          .toList();
    }
    return TopMoversResponse(
      topGainers: listFrom(json['top_gainers'] as List?),
      topLosers: listFrom(json['top_losers'] as List?),
    );
  }
}

/// One OHLC candle (backend: open_time, open, high, low, close, volume).
class CandleItem {
  const CandleItem({
    required this.openTime,
    required this.open,
    required this.high,
    required this.low,
    required this.close,
    this.volume = 0.0,
  });

  final DateTime? openTime;
  final double open;
  final double high;
  final double low;
  final double close;
  final double volume;

  static CandleItem fromJson(Map<String, dynamic> json) {
    final rawTime = json['open_time'];
    DateTime? openTime;
    if (rawTime != null) {
      openTime = DateTime.tryParse(rawTime.toString().replaceAll('Z', '+00:00'));
    }
    final toDouble = (dynamic v) {
      if (v is num) return v.toDouble();
      return double.tryParse(v?.toString() ?? '') ?? 0.0;
    };
    return CandleItem(
      openTime: openTime,
      open: toDouble(json['open']),
      high: toDouble(json['high']),
      low: toDouble(json['low']),
      close: toDouble(json['close']),
      volume: toDouble(json['volume']),
    );
  }
}

/// Client REST pour les endpoints market-data (market-summary, top-movers, bougies).
/// Avec session stockée : [SessionBearerHttp.jsonHeadersAppScoped] (même politique que l’échange).
class MarketDataApi {
  MarketDataApi({String? baseUrl}) : _baseUrl = baseUrl ?? Config.marketDataBaseUrl {
    if (kDebugMode) {
      print('[MarketDataApi] baseUrl: $_baseUrl');
    }
  }

  final String _baseUrl;

  Future<Map<String, String>> _scopedHeaders(Uri uri, String tag) =>
      SessionBearerHttp.jsonHeadersAppScoped(uri: uri, debugTag: tag);

  /// GET /api/market-data/market-summary?symbols=BTCUSDT,ETHUSDT,...
  /// Retourne la liste des résumés pour les symboles demandés.
  Future<List<MarketSummaryItem>> getMarketSummary({
    List<String>? symbols,
    List<int>? instrumentIds,
  }) async {
    if ((symbols == null || symbols.isEmpty) && (instrumentIds == null || instrumentIds.isEmpty)) {
      return [];
    }
    final query = <String, String>{};
    if (symbols != null && symbols.isNotEmpty) {
      query['symbols'] = symbols.map((s) => s.trim().toUpperCase()).join(',');
    }
    if (instrumentIds != null && instrumentIds.isNotEmpty) {
      query['instrument_ids'] = instrumentIds.join(',');
    }
    final uri = Uri.parse(Config.marketSummaryUrl).replace(queryParameters: query);
    final response = await http.get(
      uri,
      headers: await _scopedHeaders(uri, 'MarketDataApi.getMarketSummary'),
    );
    if (kDebugMode) {
      print('[MarketDataApi] market-summary: ${response.statusCode} ${response.body.length} bytes');
      if (response.statusCode != 200) print('[MarketDataApi] body: ${response.body}');
    }
    if (response.statusCode != 200) {
      throw MarketDataApiException(
        response.statusCode,
        response.body.isNotEmpty ? response.body : 'Erreur réseau',
      );
    }
    final json = jsonDecode(response.body) as Map<String, dynamic>;
    final raw = json['summaries'];
    if (raw is! List) return [];
    return raw
        .whereType<Map<String, dynamic>>()
        .map((e) => MarketSummaryItem.fromJson(e))
        .toList();
  }

  /// GET /api/market-data/top-movers?limit=10
  Future<TopMoversResponse> getTopMovers({int limit = 10}) async {
    final uri = Uri.parse(Config.topMoversUrl).replace(
      queryParameters: {'limit': limit.clamp(1, 50).toString()},
    );
    final response = await http.get(
      uri,
      headers: await _scopedHeaders(uri, 'MarketDataApi.getTopMovers'),
    );
    if (kDebugMode) {
      print('[MarketDataApi] top-movers: ${response.statusCode} ${response.body.length} bytes');
      if (response.statusCode != 200) print('[MarketDataApi] body: ${response.body}');
    }
    if (response.statusCode != 200) {
      throw MarketDataApiException(
        response.statusCode,
        response.body.isNotEmpty ? response.body : 'Erreur réseau',
      );
    }
    final json = jsonDecode(response.body) as Map<String, dynamic>;
    return TopMoversResponse.fromJson(json);
  }

  /// GET /api/market-data/candles/5m?symbol=BTCUSDT&limit=300
  Future<List<CandleItem>> getCandles5m({
    required String symbol,
    int limit = 300,
  }) async {
    return _getCandles(Config.candles5mUrl, symbol, limit, '5m');
  }

  /// GET /api/market-data/candles/1h?symbol=BTCUSDT&limit=300
  Future<List<CandleItem>> getCandles1h({
    required String symbol,
    int limit = 300,
  }) async {
    return _getCandles(Config.candles1hUrl, symbol, limit, '1h');
  }

  /// GET /api/market-data/candles/4h?symbol=BTCUSDT&limit=300
  Future<List<CandleItem>> getCandles4h({
    required String symbol,
    int limit = 300,
  }) async {
    return _getCandles(Config.candles4hUrl, symbol, limit, '4h');
  }

  /// GET /api/market-data/candles/1d?symbol=BTCUSDT&limit=300
  Future<List<CandleItem>> getCandles1d({
    required String symbol,
    int limit = 300,
  }) async {
    return _getCandles(Config.candles1dUrl, symbol, limit, '1d');
  }

  /// GET /api/market-data/candles/1w?symbol=BTCUSDT&limit=300
  Future<List<CandleItem>> getCandles1w({
    required String symbol,
    int limit = 300,
  }) async {
    return _getCandles(Config.candles1wUrl, symbol, limit, '1w');
  }

  /// GET /api/market-data/chart-history?symbol=X&period=1j|1s|1m|1a
  /// Backend impose start/end et le type de candle (5m, 1h, 4h, 1d). Retourne le max théorique dans la plage.
  Future<List<CandleItem>> getChartHistory({
    required String symbol,
    required String period,
  }) async {
    final uri = Uri.parse(Config.chartHistoryUrl).replace(
      queryParameters: {
        'symbol': symbol.trim().toUpperCase(),
        'period': period,
      },
    );
    final response = await http.get(
      uri,
      headers: await _scopedHeaders(uri, 'MarketDataApi.getChartHistory'),
    );
    if (kDebugMode) {
      print('[MarketDataApi] chart-history period=$period: ${response.statusCode}');
    }
    if (response.statusCode != 200) {
      throw MarketDataApiException(
        response.statusCode,
        response.body.isNotEmpty ? response.body : 'Erreur réseau',
      );
    }
    final json = jsonDecode(response.body) as Map<String, dynamic>;
    final raw = json['candles'];
    if (raw is! List) return [];
    return raw
        .whereType<Map<String, dynamic>>()
        .map((e) => CandleItem.fromJson(e))
        .toList();
  }

  Future<List<CandleItem>> _getCandles(String url, String symbol, int limit, String label) async {
    final uri = Uri.parse(url).replace(
      queryParameters: {
        'symbol': symbol.trim().toUpperCase(),
        'limit': limit.clamp(1, 500).toString(),
      },
    );
    final response = await http.get(
      uri,
      headers: await _scopedHeaders(uri, 'MarketDataApi._getCandles.$label'),
    );
    if (kDebugMode) {
      print('[MarketDataApi] candles/$label: ${response.statusCode} ${response.body.length} bytes');
    }
    if (response.statusCode != 200) {
      throw MarketDataApiException(
        response.statusCode,
        response.body.isNotEmpty ? response.body : 'Erreur réseau',
      );
    }
    final json = jsonDecode(response.body) as Map<String, dynamic>;
    final raw = json['candles'];
    if (raw is! List) return [];
    return raw
        .whereType<Map<String, dynamic>>()
        .map((e) => CandleItem.fromJson(e))
        .toList();
  }
}
