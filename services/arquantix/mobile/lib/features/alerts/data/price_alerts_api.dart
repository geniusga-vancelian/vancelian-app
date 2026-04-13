import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../../../core/config.dart';
import '../../../core/session_bearer_http.dart';
import '../domain/models/price_alert.dart';

class PriceAlertsApi {
  Future<Map<String, String>> _headers(Uri uri, String tag, {bool jsonBody = false}) async {
    final h = await SessionBearerHttp.jsonHeadersAppScoped(
      uri: uri,
      debugTag: tag,
      withJsonContentType: jsonBody,
    );
    return h;
  }

  Future<List<PriceAlert>> fetchAlerts({String? status, String? asset}) async {
    final params = <String, String>{};
    if (status != null) params['status'] = status;
    if (asset != null) params['asset'] = asset;
    final uri = Uri.parse(Config.alertsUrl).replace(
      queryParameters: params.isNotEmpty ? params : null,
    );
    final res = await http.get(uri, headers: await _headers(uri, 'PriceAlertsApi.fetchAlerts'));
    if (res.statusCode != 200) {
      debugPrint('[PriceAlertsApi] fetchAlerts error: ${res.statusCode}');
      return [];
    }
    final list = jsonDecode(res.body) as List;
    return list.map((e) => PriceAlert.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<PriceAlert?> createAlert({
    required String asset,
    required double targetPrice,
    required String direction,
    String priceSource = 'mid',
    String triggerMode = 'once',
  }) async {
    final uri = Uri.parse(Config.alertsUrl);
    final res = await http.post(
      uri,
      headers: await _headers(uri, 'PriceAlertsApi.createAlert', jsonBody: true),
      body: jsonEncode({
        'asset': asset,
        'target_price': targetPrice,
        'direction': direction,
        'price_source': priceSource,
        'trigger_mode': triggerMode,
      }),
    );
    if (res.statusCode != 201) {
      debugPrint('[PriceAlertsApi] createAlert error: ${res.statusCode} ${res.body}');
      return null;
    }
    return PriceAlert.fromJson(jsonDecode(res.body) as Map<String, dynamic>);
  }

  Future<bool> cancelAlert(String alertId) async {
    final uri = Uri.parse(Config.alertDeleteUrl(alertId));
    final res = await http.delete(uri, headers: await _headers(uri, 'PriceAlertsApi.cancelAlert'));
    return res.statusCode == 204;
  }

  Future<bool> deleteAllAlerts({required String asset}) async {
    final uri = Uri.parse(Config.alertsUrl).replace(
      queryParameters: {'asset': asset},
    );
    final res = await http.delete(uri, headers: await _headers(uri, 'PriceAlertsApi.deleteAllAlerts'));
    return res.statusCode == 204;
  }
}
