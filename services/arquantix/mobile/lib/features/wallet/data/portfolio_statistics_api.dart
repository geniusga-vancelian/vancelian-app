import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../core/config.dart';
import '../../../core/session_bearer_http.dart';
import '../domain/models/portfolio_statistics.dart';

class PortfolioStatisticsApi {
  const PortfolioStatisticsApi();

  Future<PortfolioStatistics> fetchStatistics() async {
    final url = Uri.parse(Config.portfolioStatisticsUrl);
    final response = await http.get(
      url,
      headers: await SessionBearerHttp.jsonHeadersAppScoped(
        uri: url,
        debugTag: 'PortfolioStatisticsApi.fetchStatistics',
      ),
    );
    if (response.statusCode != 200) {
      throw Exception('Failed to load portfolio statistics: ${response.statusCode}');
    }
    return PortfolioStatistics.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
  }
}
