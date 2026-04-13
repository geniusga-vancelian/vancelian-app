import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../core/config.dart';
import '../../../core/session_bearer_http.dart';
import '../domain/models/global_statistics.dart';

class GlobalStatisticsApi {
  const GlobalStatisticsApi();

  Future<GlobalStatistics> fetchStatistics() async {
    final url = Uri.parse(Config.globalStatisticsUrl);
    final response = await http.get(
      url,
      headers: await SessionBearerHttp.jsonHeadersAppScoped(
        uri: url,
        debugTag: 'GlobalStatisticsApi.fetchStatistics',
      ),
    );
    if (response.statusCode != 200) {
      throw Exception(
          'Failed to load global statistics: ${response.statusCode}');
    }
    return GlobalStatistics.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
  }

  Future<GlobalHistoryResult> fetchHistory({
    required String period,
  }) async {
    final url = Uri.parse(Config.globalHistoryUrl(period));
    final response = await http.get(
      url,
      headers: await SessionBearerHttp.jsonHeadersAppScoped(
        uri: url,
        debugTag: 'GlobalStatisticsApi.fetchHistory',
      ),
    );
    if (response.statusCode != 200) {
      throw Exception(
          'Failed to load global history: ${response.statusCode}');
    }
    final json = jsonDecode(response.body) as Map<String, dynamic>;
    final rawPoints = json['points'] as List<dynamic>? ?? [];
    final points = rawPoints
        .whereType<Map<String, dynamic>>()
        .map(GlobalHistoryPoint.fromJson)
        .toList(growable: false);
    final maxDd = json['max_drawdown'];
    return GlobalHistoryResult(
      points: points,
      maxDrawdown: maxDd is num ? maxDd.toDouble() : null,
    );
  }
}
