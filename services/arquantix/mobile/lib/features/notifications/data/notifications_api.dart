import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../../../core/config.dart';
import '../../../core/session_bearer_http.dart';
import '../domain/models/app_notification.dart';

class NotificationsApi {
  Future<Map<String, String>> _headers(Uri uri, String tag) =>
      SessionBearerHttp.jsonHeadersAppScoped(
        uri: uri,
        debugTag: tag,
      );

  Future<({List<AppNotification> items, int total})> fetchNotifications({
    int limit = 50,
    int offset = 0,
  }) async {
    final uri = Uri.parse(Config.notificationsUrl).replace(
      queryParameters: {'limit': '$limit', 'offset': '$offset'},
    );
    final res = await http.get(uri, headers: await _headers(uri, 'NotificationsApi.fetchNotifications'));
    if (res.statusCode != 200) {
      debugPrint('[NotificationsApi] fetchNotifications error: ${res.statusCode}');
      return (items: <AppNotification>[], total: 0);
    }
    final data = jsonDecode(res.body) as Map<String, dynamic>;
    final items = (data['items'] as List)
        .map((e) => AppNotification.fromJson(e as Map<String, dynamic>))
        .toList();
    return (items: items, total: data['total'] as int? ?? 0);
  }

  Future<int> fetchUnreadCount() async {
    final uri = Uri.parse(Config.notificationsUnreadCountUrl);
    final res = await http.get(uri, headers: await _headers(uri, 'NotificationsApi.fetchUnreadCount'));
    if (res.statusCode != 200) return 0;
    final data = jsonDecode(res.body) as Map<String, dynamic>;
    return data['count'] as int? ?? 0;
  }

  Future<bool> markRead(String notificationId) async {
    final uri = Uri.parse(Config.notificationReadUrl(notificationId));
    final res = await http.post(uri, headers: await _headers(uri, 'NotificationsApi.markRead'));
    return res.statusCode == 204;
  }

  Future<bool> markAllRead() async {
    final uri = Uri.parse(Config.notificationsReadAllUrl);
    final res = await http.post(uri, headers: await _headers(uri, 'NotificationsApi.markAllRead'));
    return res.statusCode == 204;
  }
}
