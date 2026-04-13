import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../core/config.dart';
import '../../../core/session_bearer_http.dart';

class LendingInvestApiException implements Exception {
  final int statusCode;
  final String message;

  LendingInvestApiException(this.statusCode, this.message);

  @override
  String toString() => 'LendingInvestApiException($statusCode): $message';
}

class LendingInvestPreviewResult {
  final String productId;
  final String poolAsset;
  final String fundingAsset;
  final double fundingAmount;
  final String conversionType;
  final bool requiresConversion;
  final double estimatedPoolAssetAmount;
  final double estimatedSupplyAmount;
  final String entryAssetUsed;
  final double? conversionFee;
  final String? conversionFeeAsset;

  const LendingInvestPreviewResult({
    required this.productId,
    required this.poolAsset,
    required this.fundingAsset,
    required this.fundingAmount,
    required this.conversionType,
    required this.requiresConversion,
    required this.estimatedPoolAssetAmount,
    required this.estimatedSupplyAmount,
    required this.entryAssetUsed,
    this.conversionFee,
    this.conversionFeeAsset,
  });

  factory LendingInvestPreviewResult.fromJson(Map<String, dynamic> json) {
    return LendingInvestPreviewResult(
      productId: (json['product_id'] ?? '').toString(),
      poolAsset: (json['pool_asset'] ?? '').toString(),
      fundingAsset: (json['funding_asset'] ?? '').toString(),
      fundingAmount:
          double.tryParse(json['funding_amount']?.toString() ?? '0') ?? 0,
      conversionType: (json['conversion_type'] ?? 'none').toString(),
      requiresConversion: json['requires_conversion'] == true,
      estimatedPoolAssetAmount: double.tryParse(
              json['estimated_pool_asset_amount']?.toString() ?? '0') ??
          0,
      estimatedSupplyAmount: double.tryParse(
              json['estimated_supply_amount']?.toString() ?? '0') ??
          0,
      entryAssetUsed: (json['entry_asset_used'] ?? '').toString(),
      conversionFee:
          double.tryParse(json['conversion_fee']?.toString() ?? ''),
      conversionFeeAsset: json['conversion_fee_asset'] as String?,
    );
  }
}

class LendingInvestResult {
  final String status;
  final String? commitmentId;
  final String? poolId;
  final String fundingAsset;
  final double fundingAmount;
  final String conversionType;
  final String entryAssetUsed;
  final double totalPoolAssetReceived;
  final double amountSupplied;

  const LendingInvestResult({
    required this.status,
    this.commitmentId,
    this.poolId,
    required this.fundingAsset,
    required this.fundingAmount,
    required this.conversionType,
    required this.entryAssetUsed,
    required this.totalPoolAssetReceived,
    required this.amountSupplied,
  });

  bool get isCompleted => status == 'completed';

  factory LendingInvestResult.fromJson(Map<String, dynamic> json) {
    return LendingInvestResult(
      status: (json['status'] ?? 'error').toString(),
      commitmentId: json['commitment_id']?.toString(),
      poolId: json['pool_id']?.toString(),
      fundingAsset: (json['funding_asset'] ?? '').toString(),
      fundingAmount:
          double.tryParse(json['funding_amount']?.toString() ?? '0') ?? 0,
      conversionType: (json['conversion_type'] ?? 'none').toString(),
      entryAssetUsed: (json['entry_asset_used'] ?? '').toString(),
      totalPoolAssetReceived: double.tryParse(
              json['total_pool_asset_received']?.toString() ?? '0') ??
          0,
      amountSupplied:
          double.tryParse(json['amount_supplied']?.toString() ?? '0') ?? 0,
    );
  }
}

class LendingInvestApi {
  const LendingInvestApi();

  Future<LendingInvestPreviewResult> previewInvest({
    required String productId,
    required String fundingAsset,
    required double fundingAmount,
  }) async {
    final url = Config.lendingInvestPreviewUrl(productId);
    final uri = Uri.parse(url);
    final headers = await SessionBearerHttp.jsonHeadersAppScoped(
      uri: uri,
      debugTag: 'LendingInvestApi.previewInvest',
      withJsonContentType: true,
    );
    final response = await http.post(
      uri,
      headers: headers,
      body: jsonEncode({
        'funding_asset': fundingAsset,
        'funding_amount': fundingAmount,
      }),
    );
    final json = jsonDecode(response.body) as Map<String, dynamic>;
    if (response.statusCode != 200) {
      final detail = json['detail'] ?? json['error'] ?? 'Erreur serveur';
      throw LendingInvestApiException(response.statusCode, detail.toString());
    }
    return LendingInvestPreviewResult.fromJson(json);
  }

  Future<LendingInvestResult> executeInvest({
    required String productId,
    required String fundingAsset,
    required double fundingAmount,
  }) async {
    final url = Config.lendingInvestUrl(productId);
    final uri = Uri.parse(url);
    final headers = await SessionBearerHttp.jsonHeadersAppScoped(
      uri: uri,
      debugTag: 'LendingInvestApi.executeInvest',
      withJsonContentType: true,
    );
    final response = await http.post(
      uri,
      headers: headers,
      body: jsonEncode({
        'funding_asset': fundingAsset,
        'funding_amount': fundingAmount,
      }),
    );
    final json = jsonDecode(response.body) as Map<String, dynamic>;
    if (response.statusCode != 200) {
      final detail = json['detail'] ?? json['error'] ?? 'Erreur serveur';
      throw LendingInvestApiException(response.statusCode, detail.toString());
    }
    return LendingInvestResult.fromJson(json);
  }
}
