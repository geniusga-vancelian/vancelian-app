import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../../../core/config.dart';
import '../../../core/session_bearer_http.dart';
import '../domain/models/favorite.dart';

/// Résultat de [FavoritesApi.addFavorite] (évite d’afficher « max 10 » pour toute erreur).
class AddFavoriteResult {
  const AddFavoriteResult._({
    required this.isSuccess,
    this.favorite,
    this.statusCode,
    this.detail,
  });

  final bool isSuccess;
  final Favorite? favorite;
  final int? statusCode;
  final String? detail;

  factory AddFavoriteResult.ok(Favorite f) =>
      AddFavoriteResult._(isSuccess: true, favorite: f, statusCode: 201);

  factory AddFavoriteResult.fail(int code, [String? detail]) =>
      AddFavoriteResult._(isSuccess: false, statusCode: code, detail: detail);

  /// Message utilisateur (FR) selon le code HTTP / le corps FastAPI.
  String messageForUser() {
    if (isSuccess) return '';
    final c = statusCode ?? 0;
    if (c == 409) {
      return 'Maximum 10 favoris atteint pour ce type.';
    }
    if (c == 404) {
      return 'Favoris indisponibles : connectez-vous ou terminez l’inscription.';
    }
    if (c == 400 || c == 422) {
      return detail ?? 'Requête invalide.';
    }
    if (c >= 500) {
      return 'Service temporairement indisponible. Réessayez.';
    }
    if (detail != null && detail!.isNotEmpty) return detail!;
    return 'Impossible d\'ajouter aux favoris.';
  }
}

String? _parseFastApiDetail(String body) {
  try {
    final decoded = jsonDecode(body);
    if (decoded is! Map) return null;
    final d = decoded['detail'];
    if (d is String) return d;
    if (d is List && d.isNotEmpty) {
      final first = d.first;
      if (first is Map) {
        final msg = first['msg'];
        if (msg is String) return msg;
      }
    }
  } catch (_) {}
  return null;
}

class FavoritesApi {
  Future<Map<String, String>> _headers(Uri uri, String tag) =>
      SessionBearerHttp.jsonHeadersAppScoped(
        uri: uri,
        debugTag: tag,
      );

  Future<List<Favorite>> fetchFavorites({String? entityType}) async {
    final params = <String, String>{};
    if (entityType != null) params['entity_type'] = entityType;
    final uri = Uri.parse(Config.favoritesUrl).replace(
      queryParameters: params.isNotEmpty ? params : null,
    );
    final res = await http.get(
      uri,
      headers: await _headers(uri, 'FavoritesApi.fetchFavorites'),
    );
    if (res.statusCode != 200) {
      debugPrint('[FavoritesApi] fetchFavorites error: ${res.statusCode}');
      return [];
    }
    final list = jsonDecode(res.body) as List;
    return list.map((e) => Favorite.fromJson(e as Map<String, dynamic>)).toList();
  }

  Future<AddFavoriteResult> addFavorite({
    required String entityType,
    required String entityId,
  }) async {
    final uri = Uri.parse(Config.favoritesUrl);
    final headers = await _headers(uri, 'FavoritesApi.addFavorite');
    headers['Content-Type'] = 'application/json';
    final res = await http.post(
      uri,
      headers: headers,
      body: jsonEncode({
        'entity_type': entityType,
        'entity_id': entityId,
      }),
    );
    if (res.statusCode == 201 || res.statusCode == 200) {
      return AddFavoriteResult.ok(
        Favorite.fromJson(jsonDecode(res.body) as Map<String, dynamic>),
      );
    }
    debugPrint('[FavoritesApi] addFavorite error: ${res.statusCode} ${res.body}');
    return AddFavoriteResult.fail(res.statusCode, _parseFastApiDetail(res.body));
  }

  Future<bool> removeFavorite(String favoriteId) async {
    final uri = Uri.parse(Config.favoriteDeleteUrl(favoriteId));
    final res = await http.delete(uri, headers: await _headers(uri, 'FavoritesApi.removeFavorite'));
    return res.statusCode == 204;
  }

  Future<bool> removeFavoriteByEntity({
    required String entityType,
    required String entityId,
  }) async {
    final uri = Uri.parse(Config.favoritesUrl).replace(
      queryParameters: {
        'entity_type': entityType,
        'entity_id': entityId,
      },
    );
    final res = await http.delete(uri, headers: await _headers(uri, 'FavoritesApi.removeFavoriteByEntity'));
    return res.statusCode == 204;
  }
}
