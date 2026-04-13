import 'dart:convert';
import 'dart:developer' as developer;

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../../../../core/config.dart';
import '../../../../core/http_error_display.dart';
import '../../../../core/session_bearer_http.dart';
import 'mobile_app_profile.dart';
import 'patch_security_preferences_result.dart';

class MobileProfileApi {
  const MobileProfileApi();

  /// Profil Mon compte : Bearer obligatoire (jeton session ou [accessToken] explicite).
  ///
  /// Sans jeton : [MissingBearerTokenException] — pas de requête anonyme silencieuse.
  Future<MobileAppProfile?> fetchProfile({String? accessToken}) async {
    final uri = Uri.parse(Config.mobileAppProfileUrl);
    final headers = await SessionBearerHttp.jsonHeaders(
      uri: uri,
      debugTag: 'MobileProfileApi.fetchProfile',
      policy: SessionBearerPolicy.required,
      overrideAccessToken: accessToken,
    );
    final res = await http
        .get(uri, headers: headers)
        .timeout(const Duration(seconds: 4));
    if (res.statusCode != 200) {
      if (kDebugMode) {
        debugPrint(
          '[MobileProfileApi] GET profile HTTP ${res.statusCode} '
          'bodyLen=${res.body.length}',
        );
      }
      return null;
    }
    final body = res.body;
    if (responseBodyLooksLikeNonJsonApi(body)) return null;
    try {
      final json = jsonDecode(body) as Map<String, dynamic>;
      return MobileAppProfile.fromJson(json);
    } catch (_) {
      return null;
    }
  }

  static void _logPatch({
    required String phase,
    required Uri uri,
    String? domain,
    int? status,
    String? resultKind,
    String? extra,
  }) {
    final safePath = uri.path.isEmpty ? '/' : uri.path;
    developer.log(
      [
        phase,
        'path=$safePath',
        if (domain != null) 'domain=$domain',
        if (status != null) 'http=$status',
        if (resultKind != null) 'result=$resultKind',
        if (extra != null) extra,
      ].join(' '),
      name: 'sec_prefs.patch',
    );
  }

  /// PATCH V1 structuré uniquement (pas de booléens legacy plats).
  Future<PatchSecurityPreferencesResult> patchSecurityPreferencesV1({
    String? accessToken,
    Map<String, dynamic>? biometric,
    Map<String, dynamic>? pushNotifications,
  }) async {
    final body = <String, dynamic>{};
    if (biometric != null && biometric.isNotEmpty) {
      body['biometric'] = biometric;
    }
    if (pushNotifications != null && pushNotifications.isNotEmpty) {
      body['push_notifications'] = pushNotifications;
    }
    if (body.isEmpty) {
      return const PatchSecurityPreferencesFailure(
        PatchSecurityPreferencesFailureKind.clientError,
        detail: 'empty_body',
      );
    }

    final uri = Uri.parse(Config.mobileSecurityPreferencesUrl);
    final domain = biometric != null ? 'biometric' : 'push_notifications';

    try {
      final headers = await SessionBearerHttp.jsonHeadersAppScoped(
        uri: uri,
        debugTag: 'MobileProfileApi.patchSecurityPreferencesV1',
        overrideAccessToken: accessToken,
        withJsonContentType: true,
      );
      _logPatch(
        phase: 'request',
        uri: uri,
        domain: domain,
        extra: 'hasBiometric=${biometric != null} hasPush=${pushNotifications != null}',
      );
      final res = await http
          .patch(uri, headers: headers, body: jsonEncode(body))
          .timeout(const Duration(seconds: 12));
      final out = patchSecurityPreferencesResultFromHttp(
        statusCode: res.statusCode,
        body: res.body,
      );
      final kindStr = switch (out) {
        PatchSecurityPreferencesSuccess() => 'success',
        PatchSecurityPreferencesFailure(:final kind, :final detail) =>
          '${kind.name}${detail != null ? ':$detail' : ''}',
      };
      _logPatch(
        phase: 'response',
        uri: uri,
        domain: domain,
        status: res.statusCode,
        resultKind: kindStr,
      );
      if (out is PatchSecurityPreferencesFailure &&
          out.kind == PatchSecurityPreferencesFailureKind.validation422 &&
          kDebugMode) {
        debugPrint(
          '[MobileProfileApi] PATCH security 422 body=${res.body}',
        );
      }
      return out;
    } on MissingBearerTokenException catch (e) {
      _logPatch(
        phase: 'bearer_missing',
        uri: uri,
        domain: domain,
        extra: 'tag=${e.debugTag}',
      );
      return const PatchSecurityPreferencesFailure(
        PatchSecurityPreferencesFailureKind.sessionMissing,
        detail: 'missing_bearer',
      );
    } on Exception catch (e) {
      if (kDebugMode) {
        debugPrint('[MobileProfileApi] PATCH security network error: $e');
      }
      _logPatch(
        phase: 'exception',
        uri: uri,
        domain: domain,
        extra: e.toString(),
      );
      return PatchSecurityPreferencesFailure(
        PatchSecurityPreferencesFailureKind.network,
        detail: e.toString(),
      );
    }
  }
}
