import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../../../core/config.dart';
import '../../../core/session_bearer_http.dart';
import '../domain/models/trigger_order.dart';

class TriggerOrdersApi {
  Future<Map<String, String>> _headers(Uri uri, String tag, {bool jsonBody = false}) async {
    return SessionBearerHttp.jsonHeadersAppScoped(
      uri: uri,
      debugTag: tag,
      withJsonContentType: jsonBody,
    );
  }

  Future<List<TriggerOrder>> fetchOrders({String? status, String? asset}) async {
    final params = <String, String>{};
    if (status != null) params['status'] = status;
    if (asset != null) params['asset'] = asset;
    final uri = Uri.parse(Config.ordersUrl).replace(
      queryParameters: params.isNotEmpty ? params : null,
    );
    final res = await http.get(uri, headers: await _headers(uri, 'TriggerOrdersApi.fetchOrders'));
    if (res.statusCode != 200) {
      debugPrint('[TriggerOrdersApi] fetchOrders error: ${res.statusCode}');
      return [];
    }
    final list = jsonDecode(res.body) as List;
    return list.map((e) => TriggerOrder.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<TriggerOrder?> createOrder({
    required String asset,
    required String side,
    required String orderType,
    required double triggerPrice,
    required double amount,
    int? slippageBps,
  }) async {
    final body = <String, dynamic>{
      'asset': asset,
      'side': side,
      'order_type': orderType,
      'trigger_price': triggerPrice,
      'amount': amount,
    };
    if (slippageBps != null) body['slippage_bps'] = slippageBps;

    final uri = Uri.parse(Config.ordersUrl);
    final res = await http.post(
      uri,
      headers: await _headers(uri, 'TriggerOrdersApi.createOrder', jsonBody: true),
      body: jsonEncode(body),
    );
    if (res.statusCode != 201) {
      debugPrint('[TriggerOrdersApi] createOrder error: ${res.statusCode} ${res.body}');
      return null;
    }
    return TriggerOrder.fromJson(jsonDecode(res.body) as Map<String, dynamic>);
  }

  Future<bool> cancelOrder(String orderId) async {
    final uri = Uri.parse(Config.orderDeleteUrl(orderId));
    final res = await http.delete(uri, headers: await _headers(uri, 'TriggerOrdersApi.cancelOrder'));
    return res.statusCode == 204;
  }
}
