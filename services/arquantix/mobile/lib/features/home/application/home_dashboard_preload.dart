import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../../../core/config.dart';
import '../../../core/currency_preference.dart';
import '../../../core/http_error_display.dart';
import '../../../core/profile_identity_coordinator.dart';
import '../../../core/profile_leading_preference.dart';
import '../../../core/session_bearer_http.dart';
import '../../../core/session_identity_context.dart';
import '../../../features/home/data/dashboard_layout_api.dart';
import '../../../features/news/data/blog_api.dart';
import '../../../features/security/passcode/data/session_service.dart';

/// Préchargement après déverrouillage passcode : aligné sur le premier cycle
/// [HomeScreen._loadAll] (bootstrap, profil, layout, fil d’actus) pour limiter
/// les sauts visuels à l’arrivée sur le dashboard.
class HomeDashboardPreload {
  HomeDashboardPreload._();

  static Future<void> runAfterPasscodeUnlock() async {
    final hasSession = await SessionService.instance.hasSessionCredentials();
    if (!hasSession) {
      return;
    }

    await Future.wait([
      _prefetchBootstrap(),
      ProfileIdentityCoordinator.instance.refreshDisplayIdentity(
        debugTag: 'HomeDashboardPreload',
      ),
      _prefetchDashboardLayout(),
      _prefetchBlogFeed(),
    ]);
  }

  /// Même logique que [HomeScreen._loadBootstrap] (sans setState).
  static Future<void> _prefetchBootstrap() async {
    try {
      final accessToken = await SessionService.instance.readAccessToken();
      final expectAuth =
          await SessionService.instance.hasSessionCredentials();
      if (expectAuth &&
          (accessToken == null || accessToken.trim().isEmpty)) {
        return;
      }

      Future<void> applyBody(String body) async {
        if (responseBodyLooksLikeNonJsonApi(body)) {
          return;
        }
        try {
          final json = jsonDecode(body) as Map<String, dynamic>;
          final client = json['client'] as Map<String, dynamic>? ?? {};
          final cid = client['id'];
          if (cid != null) {
            SessionIdentityContext.instance
                .hydrateResolvedClientIdFromBootstrap(cid.toString());
          }
          CurrencyPreference.instance.loadFromBootstrap(
            client['reference_currency'] as String?,
          );
          ProfileLeadingPreference.instance.loadFromBootstrapJson(
            client['initials'],
          );
        } catch (e) {
          debugPrint('[HomeDashboardPreload] bootstrap JSON parse: $e');
        }
      }

      final bootstrapUri = Uri.parse(Config.bootstrapUrl);
      final bootstrapHeaders = await SessionBearerHttp.jsonHeadersAppScoped(
        uri: bootstrapUri,
        debugTag: 'HomeDashboardPreload.bootstrap',
        overrideAccessToken: accessToken,
      );

      final res = await http.get(
        bootstrapUri,
        headers: bootstrapHeaders,
      );
      if (res.statusCode == 200) {
        await applyBody(res.body);
      }
    } catch (e) {
      debugPrint('[HomeDashboardPreload] bootstrap: $e');
    }
  }

  static Future<void> _prefetchDashboardLayout() async {
    try {
      final api = DashboardLayoutApi();
      await api.getDashboardLayout(forceRefresh: false);
    } catch (e) {
      debugPrint('[HomeDashboardPreload] dashboard layout: $e');
    }
  }

  static Future<void> _prefetchBlogFeed() async {
    try {
      final api = BlogApi();
      await api.getFeed(locale: 'fr', page: 1, pageSize: 20);
    } catch (e) {
      debugPrint('[HomeDashboardPreload] blog feed: $e');
    }
  }
}
