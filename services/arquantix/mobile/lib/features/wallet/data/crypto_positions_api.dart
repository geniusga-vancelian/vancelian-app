import 'dart:convert';
import 'package:http/http.dart' as http;

import '../../../core/config.dart';
import '../../../core/session_bearer_http.dart';
import '../domain/models/crypto_positions_data.dart';
import '../domain/models/crypto_wallet_detail.dart';

class CryptoPositionsApiException implements Exception {
  final String message;
  final int? statusCode;
  CryptoPositionsApiException(this.message, {this.statusCode});

  @override
  String toString() => 'CryptoPositionsApiException($statusCode): $message';
}

class CryptoPositionsApi {
  const CryptoPositionsApi();

  Future<Map<String, String>> _headers(Uri url, String tag) =>
      SessionBearerHttp.jsonHeadersAppScoped(
        uri: url,
        debugTag: tag,
      );

  Future<CryptoPositionsData> fetchPositions() async {
    final url = Uri.parse(Config.cryptoPositionsUrl);
    final response = await http.get(
      url,
      headers: await _headers(url, 'CryptoPositionsApi.fetchPositions'),
    );

    if (response.statusCode == 404) {
      throw CryptoPositionsApiException(
        'Session ou profil client introuvable (connexion / inscription requise).',
        statusCode: 404,
      );
    }

    if (response.statusCode != 200) {
      throw CryptoPositionsApiException(
        'Failed to fetch crypto positions',
        statusCode: response.statusCode,
      );
    }

    final json = jsonDecode(response.body) as Map<String, dynamic>;
    return CryptoPositionsData.fromJson(json);
  }

  /// Fetch only direct (non-bundle) holdings from the direct portfolio overlay.
  Future<CryptoPositionsData> fetchDirectPositions() async {
    final url = Uri.parse(Config.directCryptoPositionsUrl);
    final response = await http.get(
      url,
      headers: await _headers(url, 'CryptoPositionsApi.fetchDirectPositions'),
    );

    if (response.statusCode == 404) {
      throw CryptoPositionsApiException(
        'Session ou profil client introuvable (connexion / inscription requise).',
        statusCode: 404,
      );
    }

    if (response.statusCode != 200) {
      throw CryptoPositionsApiException(
        'Failed to fetch direct crypto positions',
        statusCode: response.statusCode,
      );
    }

    final json = jsonDecode(response.body) as Map<String, dynamic>;
    return CryptoPositionsData.fromJson(json);
  }

  Future<CryptoWalletDetail> fetchDetail(String asset) async {
    final url = Uri.parse(Config.cryptoWalletDetailUrl(asset));
    final response = await http.get(
      url,
      headers: await _headers(url, 'CryptoPositionsApi.fetchDetail'),
    );

    if (response.statusCode == 404) {
      throw CryptoPositionsApiException(
        'Position not found',
        statusCode: 404,
      );
    }

    if (response.statusCode != 200) {
      throw CryptoPositionsApiException(
        'Failed to fetch crypto detail',
        statusCode: response.statusCode,
      );
    }

    final json = jsonDecode(response.body) as Map<String, dynamic>;
    final detail = json['detail'] as Map<String, dynamic>?;
    if (detail == null) {
      throw CryptoPositionsApiException('No detail found', statusCode: 404);
    }
    return CryptoWalletDetail.fromJson(detail);
  }

  Future<List<CryptoTransactionItem>> fetchTransactions(String asset) async {
    final url = Uri.parse(Config.cryptoTransactionsUrl(asset));
    final response = await http.get(
      url,
      headers: await _headers(url, 'CryptoPositionsApi.fetchTransactions'),
    );

    if (response.statusCode != 200) {
      throw CryptoPositionsApiException(
        'Failed to fetch crypto transactions',
        statusCode: response.statusCode,
      );
    }

    final json = jsonDecode(response.body) as Map<String, dynamic>;
    final list = json['transactions'] as List<dynamic>? ?? [];
    return list
        .map((e) => CryptoTransactionItem.fromJson(e as Map<String, dynamic>))
        .toList();
  }
}

class CryptoTransactionItem {
  const CryptoTransactionItem({
    required this.id,
    required this.side,
    required this.asset,
    required this.amountCrypto,
    required this.amountFiat,
    required this.price,
    required this.currency,
    required this.status,
    this.feeAmount,
    this.feeAsset,
    this.externalReference,
    required this.createdAt,
    required this.title,
    required this.subtitle,
    required this.direction,
    this.fromAsset,
    this.toAsset,
  });

  final String id;
  final String side;
  final String asset;
  final String amountCrypto;
  final String amountFiat;
  final String price;
  final String currency;
  final String status;
  final String? feeAmount;
  final String? feeAsset;
  final String? externalReference;
  final DateTime createdAt;
  final String title;
  final String subtitle;
  final String direction;
  final String? fromAsset;
  final String? toAsset;

  bool get isSwap =>
      fromAsset != null &&
      toAsset != null &&
      fromAsset!.toUpperCase() != currency.toUpperCase();

  factory CryptoTransactionItem.fromJson(Map<String, dynamic> json) {
    return CryptoTransactionItem(
      id: json['id'] as String? ?? '',
      side: json['side'] as String? ?? '',
      asset: json['asset'] as String? ?? '',
      amountCrypto: json['amount_crypto'] as String? ?? '0',
      amountFiat: json['amount_fiat'] as String? ?? '0',
      price: json['price'] as String? ?? '0',
      currency: json['currency'] as String? ?? 'EUR',
      status: json['status'] as String? ?? 'unknown',
      feeAmount: json['fee_amount'] as String?,
      feeAsset: json['fee_asset'] as String?,
      externalReference: json['external_reference'] as String?,
      createdAt: DateTime.tryParse(json['created_at']?.toString() ?? '') ?? DateTime.now(),
      title: json['title'] as String? ?? '',
      subtitle: json['subtitle'] as String? ?? '',
      direction: json['direction'] as String? ?? '',
      fromAsset: json['from_asset'] as String?,
      toAsset: json['to_asset'] as String?,
    );
  }
}
