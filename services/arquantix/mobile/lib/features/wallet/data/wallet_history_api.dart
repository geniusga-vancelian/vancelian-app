import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../core/config.dart';
import '../../../core/session_bearer_http.dart';

class WalletHistoryPoint {
  const WalletHistoryPoint({required this.timestamp, required this.walletValue});

  final DateTime timestamp;
  final double walletValue;

  factory WalletHistoryPoint.fromJson(Map<String, dynamic> json) {
    return WalletHistoryPoint(
      timestamp: DateTime.parse(json['timestamp'] as String),
      walletValue: (json['wallet_value'] as num).toDouble(),
    );
  }
}

class WalletHistoryData {
  const WalletHistoryData({required this.currency, required this.points});

  final String currency;
  final List<WalletHistoryPoint> points;

  factory WalletHistoryData.fromJson(Map<String, dynamic> json) {
    final raw = json['points'] as List? ?? [];
    return WalletHistoryData(
      currency: (json['currency'] ?? 'EUR') as String,
      points: raw
          .whereType<Map<String, dynamic>>()
          .map(WalletHistoryPoint.fromJson)
          .toList(growable: false),
    );
  }
}

class WalletHistoryApi {
  const WalletHistoryApi();

  Future<Map<String, String>> _headers(Uri url, String tag) =>
      SessionBearerHttp.jsonHeadersAppScoped(
        uri: url,
        debugTag: tag,
      );

  Future<WalletHistoryData> fetchHistory({
    String period = 'ALL',
    String? asset,
    String? mode,
    String? scope,
    String? portfolioScope,
    String? portfolioId,
  }) async {
    final url = Uri.parse(Config.walletHistoryUrl(
      period,
      asset: asset,
      mode: mode,
      scope: scope,
      portfolioScope: portfolioScope,
      portfolioId: portfolioId,
    ));
    final response = await http.get(
      url,
      headers: await _headers(url, 'WalletHistoryApi.fetchHistory'),
    );

    if (response.statusCode != 200) {
      throw Exception('wallet_history_error: ${response.statusCode}');
    }

    final json = jsonDecode(response.body) as Map<String, dynamic>;
    return WalletHistoryData.fromJson(json);
  }

  Future<WalletHistoryData> fetchBundleHistory({
    required String portfolioId,
    String period = 'ALL',
    String? asset,
    String? mode,
  }) async {
    final url = Uri.parse(Config.bundleHistoryUrl(portfolioId, period, asset: asset, mode: mode));
    final response = await http.get(
      url,
      headers: await _headers(url, 'WalletHistoryApi.fetchBundleHistory'),
    );

    if (response.statusCode != 200) {
      throw Exception('bundle_history_error: ${response.statusCode}');
    }

    final json = jsonDecode(response.body) as Map<String, dynamic>;
    return WalletHistoryData.fromJson(json);
  }
}
