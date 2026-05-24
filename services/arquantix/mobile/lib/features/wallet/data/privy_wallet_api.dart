import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../core/config.dart';
import '../../../core/session_bearer_http.dart';

class PrivyWalletApiException implements Exception {
  PrivyWalletApiException(this.message, {this.statusCode});

  final String message;
  final int? statusCode;

  @override
  String toString() => 'PrivyWalletApiException($statusCode): $message';
}

class PrivyWalletApi {
  const PrivyWalletApi();

  Future<Map<String, String>> _headers(Uri url, String tag) =>
      SessionBearerHttp.jsonHeadersAppScoped(
        uri: url,
        debugTag: tag,
      );

  Future<PrivyWalletBalancesData> fetchBalances() async {
    final url = Uri.parse(Config.privyWalletBalancesUrl);
    final response = await http.get(
      url,
      headers: await _headers(url, 'PrivyWalletApi.fetchBalances'),
    );

    if (response.statusCode == 401) {
      throw PrivyWalletApiException('Session requise.', statusCode: 401);
    }
    if (response.statusCode != 200) {
      throw PrivyWalletApiException(
        'Impossible de charger les soldes Privy.',
        statusCode: response.statusCode,
      );
    }

    final json = jsonDecode(response.body) as Map<String, dynamic>;
    return PrivyWalletBalancesData.fromJson(json);
  }

  Future<List<PrivyWalletDepositItem>> fetchDeposits({String? asset, int limit = 100}) async {
    final params = <String, String>{'limit': '$limit'};
    if (asset != null && asset.trim().isNotEmpty) {
      params['asset'] = asset.trim().toUpperCase();
    }
    final url = Uri.parse(Config.privyWalletDepositsUrl).replace(queryParameters: params);
    final response = await http.get(
      url,
      headers: await _headers(url, 'PrivyWalletApi.fetchDeposits'),
    );

    if (response.statusCode == 401) {
      throw PrivyWalletApiException('Session requise.', statusCode: 401);
    }
    if (response.statusCode != 200) {
      throw PrivyWalletApiException(
        'Impossible de charger les dépôts Privy.',
        statusCode: response.statusCode,
      );
    }

    final json = jsonDecode(response.body) as Map<String, dynamic>;
    final list = json['deposits'] as List<dynamic>? ?? [];
    return list
        .map((e) => PrivyWalletDepositItem.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<PrivyWalletDepositItem> fetchDepositDetail(String depositId) async {
    final url = Uri.parse(Config.privyWalletDepositDetailUrl(depositId));
    final response = await http.get(
      url,
      headers: await _headers(url, 'PrivyWalletApi.fetchDepositDetail'),
    );

    if (response.statusCode == 404) {
      throw PrivyWalletApiException('Dépôt introuvable.', statusCode: 404);
    }
    if (response.statusCode != 200) {
      throw PrivyWalletApiException(
        'Impossible de charger le dépôt.',
        statusCode: response.statusCode,
      );
    }

    final json = jsonDecode(response.body) as Map<String, dynamic>;
    return PrivyWalletDepositItem.fromJson(json);
  }
}

class PrivyWalletBalanceItem {
  const PrivyWalletBalanceItem({
    required this.asset,
    required this.name,
    required this.balance,
    required this.availableBalance,
    required this.iconKey,
    this.walletAddress,
    this.chainType,
    this.chainId,
  });

  final String asset;
  final String name;
  final String balance;
  final String availableBalance;
  final String iconKey;
  final String? walletAddress;
  final String? chainType;
  final int? chainId;

  factory PrivyWalletBalanceItem.fromJson(Map<String, dynamic> json) {
    return PrivyWalletBalanceItem(
      asset: json['asset'] as String? ?? '',
      name: json['name'] as String? ?? '',
      balance: json['balance'] as String? ?? '0',
      availableBalance: json['available_balance'] as String? ?? '0',
      iconKey: json['icon_key'] as String? ?? '',
      walletAddress: json['wallet_address'] as String?,
      chainType: json['chain_type'] as String?,
      chainId: json['chain_id'] as int?,
    );
  }
}

class PrivyWalletBalancesData {
  const PrivyWalletBalancesData({
    required this.positionsCount,
    required this.walletCount,
    required this.balances,
  });

  final int positionsCount;
  final int walletCount;
  final List<PrivyWalletBalanceItem> balances;

  factory PrivyWalletBalancesData.fromJson(Map<String, dynamic> json) {
    final summary = json['summary'] as Map<String, dynamic>? ?? {};
    final list = json['balances'] as List<dynamic>? ?? [];
    return PrivyWalletBalancesData(
      positionsCount: summary['positions_count'] as int? ?? list.length,
      walletCount: summary['wallet_count'] as int? ?? 0,
      balances: list
          .map((e) => PrivyWalletBalanceItem.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}

class PrivyWalletDepositItem {
  const PrivyWalletDepositItem({
    required this.id,
    required this.transactionKind,
    required this.direction,
    required this.asset,
    required this.amount,
    required this.status,
    required this.chainType,
    this.chainId,
    required this.txHash,
    this.fromAddress,
    required this.toAddress,
    required this.confirmations,
    required this.title,
    this.subtitle,
    this.walletAddress,
    required this.createdAt,
    this.confirmedAt,
  });

  final String id;
  final String transactionKind;
  final String direction;
  final String asset;
  final String amount;
  final String status;
  final String chainType;
  final int? chainId;
  final String txHash;
  final String? fromAddress;
  final String toAddress;
  final int confirmations;
  final String title;
  final String? subtitle;
  final String? walletAddress;
  final DateTime createdAt;
  final DateTime? confirmedAt;

  bool get isCredit => direction == 'credit';

  factory PrivyWalletDepositItem.fromJson(Map<String, dynamic> json) {
    return PrivyWalletDepositItem(
      id: json['id'] as String? ?? '',
      transactionKind: json['transaction_kind'] as String? ?? 'privy_deposit_in',
      direction: json['direction'] as String? ?? 'credit',
      asset: json['asset'] as String? ?? '',
      amount: json['amount'] as String? ?? '0',
      status: json['status'] as String? ?? 'confirmed',
      chainType: json['chain_type'] as String? ?? 'ethereum',
      chainId: json['chain_id'] as int?,
      txHash: json['tx_hash'] as String? ?? '',
      fromAddress: json['from_address'] as String?,
      toAddress: json['to_address'] as String? ?? '',
      confirmations: json['confirmations'] as int? ?? 0,
      title: json['title'] as String? ?? '',
      subtitle: json['subtitle'] as String?,
      walletAddress: json['wallet_address'] as String?,
      createdAt: DateTime.tryParse(json['created_at']?.toString() ?? '') ?? DateTime.now(),
      confirmedAt: json['confirmed_at'] != null
          ? DateTime.tryParse(json['confirmed_at'].toString())
          : null,
    );
  }
}
