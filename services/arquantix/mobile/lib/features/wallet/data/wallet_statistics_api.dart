import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../core/config.dart';
import '../../../core/session_bearer_http.dart';
import '../domain/models/wallet_statistics.dart';

class WalletStatisticsApi {
  const WalletStatisticsApi();

  Future<WalletStatistics> fetchStatistics(
    String asset, {
    String? portfolioScope,
    String? portfolioId,
  }) async {
    final url = Uri.parse(Config.walletStatisticsUrl(
      asset,
      portfolioScope: portfolioScope,
      portfolioId: portfolioId,
    ));
    final response = await http.get(
      url,
      headers: await SessionBearerHttp.jsonHeadersAppScoped(
        uri: url,
        debugTag: 'WalletStatisticsApi.fetchStatistics',
      ),
    );
    if (response.statusCode != 200) {
      throw Exception('Failed to load wallet statistics: ${response.statusCode}');
    }
    return WalletStatistics.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
  }
}
