import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../core/config.dart';
import '../../../core/session_bearer_http.dart';
import 'exchange_api.dart';

class BundleInvestResult {
  const BundleInvestResult({
    required this.status,
    this.batchId,
    this.portfolioId,
    this.entryAsset,
    this.funding,
    this.totalEntryAssetReceived,
    this.totalEntryAssetConsumed,
    this.cashLegRemaining,
    this.legsSucceeded,
    this.legsFailed,
    this.allocationDetails,
    this.errorCode,
    this.message,
  });

  final String status;
  final String? batchId;
  final String? portfolioId;
  final String? entryAsset;
  final Map<String, dynamic>? funding;
  final double? totalEntryAssetReceived;
  final double? totalEntryAssetConsumed;
  final double? cashLegRemaining;
  final int? legsSucceeded;
  final int? legsFailed;
  final List<BundleAllocationLeg>? allocationDetails;
  final String? errorCode;
  final String? message;

  bool get isCompleted => status == 'completed';
  bool get isPartial => status == 'partial';
  bool get isFailed => status == 'failed';
  bool get isSuccess => isCompleted || isPartial;

  factory BundleInvestResult.fromJson(Map<String, dynamic> json) {
    final rawDetails = json['allocation_details'] as List<dynamic>? ?? [];
    return BundleInvestResult(
      status: json['status'] as String? ?? 'failed',
      batchId: json['batch_id'] as String?,
      portfolioId: json['portfolio_id'] as String?,
      entryAsset: json['entry_asset'] as String?,
      funding: json['funding'] as Map<String, dynamic>?,
      totalEntryAssetReceived: _num(json['total_entry_asset_received']),
      totalEntryAssetConsumed: _num(json['total_entry_asset_consumed']),
      cashLegRemaining: _num(json['cash_leg_remaining']),
      legsSucceeded: json['legs_succeeded'] as int?,
      legsFailed: json['legs_failed'] as int?,
      allocationDetails: rawDetails
          .map((e) => BundleAllocationLeg.fromJson(e as Map<String, dynamic>))
          .toList(),
      errorCode: json['error_code'] as String? ?? json['error'] as String?,
      message: json['message'] as String?,
    );
  }

  static double? _num(dynamic v) {
    if (v == null) return null;
    return double.tryParse(v.toString());
  }
}

class BundleAllocationLeg {
  const BundleAllocationLeg({
    required this.asset,
    required this.targetWeight,
    required this.entryAssetConsumed,
    required this.cryptoReceived,
    required this.status,
    this.error,
  });

  final String asset;
  final double targetWeight;
  final double entryAssetConsumed;
  final double cryptoReceived;
  final String status;
  final String? error;

  bool get isCompleted => status == 'completed';

  factory BundleAllocationLeg.fromJson(Map<String, dynamic> json) {
    return BundleAllocationLeg(
      asset: json['asset'] as String? ?? '',
      targetWeight: (json['target_weight'] as num?)?.toDouble() ?? 0,
      entryAssetConsumed: (json['entry_asset_consumed'] as num?)?.toDouble() ?? 0,
      cryptoReceived: (json['crypto_received'] as num?)?.toDouble() ?? 0,
      status: json['status'] as String? ?? 'unknown',
      error: json['error'] as String?,
    );
  }
}

class BundleStatusResult {
  const BundleStatusResult({
    required this.portfolioId,
    required this.portfolioName,
    required this.status,
    required this.cashLegs,
    required this.allocatedPositions,
    required this.totalCostBasis,
  });

  final String portfolioId;
  final String portfolioName;
  final String status;
  final List<BundlePositionInfo> cashLegs;
  final List<BundlePositionInfo> allocatedPositions;
  final double totalCostBasis;

  factory BundleStatusResult.fromJson(Map<String, dynamic> json) {
    final rawCash = json['cash_legs'] as List<dynamic>? ?? [];
    final rawAlloc = json['allocated_positions'] as List<dynamic>? ?? [];
    return BundleStatusResult(
      portfolioId: json['portfolio_id'] as String? ?? '',
      portfolioName: json['portfolio_name'] as String? ?? '',
      status: json['status'] as String? ?? '',
      cashLegs: rawCash
          .map((e) => BundlePositionInfo.fromJson(e as Map<String, dynamic>))
          .toList(),
      allocatedPositions: rawAlloc
          .map((e) => BundlePositionInfo.fromJson(e as Map<String, dynamic>))
          .toList(),
      totalCostBasis: (json['total_cost_basis'] as num?)?.toDouble() ?? 0,
    );
  }
}

class BundlePositionInfo {
  const BundlePositionInfo({
    required this.asset,
    required this.quantity,
    required this.costBasis,
    required this.positionType,
    this.marketValue,
    this.priceEur,
    this.targetWeight,
  });

  final String asset;
  final double quantity;
  final double costBasis;
  final String positionType;
  final double? marketValue;
  final double? priceEur;
  final double? targetWeight;

  bool get isCash => positionType == 'cash';
  bool get isSpot => positionType == 'spot';

  factory BundlePositionInfo.fromJson(Map<String, dynamic> json) {
    return BundlePositionInfo(
      asset: json['asset'] as String? ?? '',
      quantity: (json['quantity'] as num?)?.toDouble() ?? 0,
      costBasis: (json['cost_basis'] as num?)?.toDouble() ?? 0,
      positionType: json['position_type'] as String? ?? '',
      marketValue: (json['market_value'] as num?)?.toDouble(),
      priceEur: (json['price_eur'] as num?)?.toDouble(),
      targetWeight: (json['target_weight'] as num?)?.toDouble(),
    );
  }
}

class BundleInvestPreviewResult {
  const BundleInvestPreviewResult({
    required this.previewStatus,
    this.bundleId,
    this.bundleName,
    this.fundingAsset,
    this.fundingAmount,
    this.entryAssetUsed,
    this.estimatedEntryAssetAmount,
    this.estimatedRemainingEntryAsset,
    this.allocations = const [],
    this.warnings = const [],
  });

  final String previewStatus;
  final String? bundleId;
  final String? bundleName;
  final String? fundingAsset;
  final String? fundingAmount;
  final String? entryAssetUsed;
  final String? estimatedEntryAssetAmount;
  final String? estimatedRemainingEntryAsset;
  final List<BundlePreviewAllocation> allocations;
  final List<String> warnings;

  bool get isOk => previewStatus == 'ok';
  bool get isPartial => previewStatus == 'partial';
  bool get isInvalid => previewStatus == 'invalid';
  bool get isUsable => isOk || isPartial;

  double get entryAssetAmountDouble =>
      double.tryParse(estimatedEntryAssetAmount ?? '') ?? 0;
  double get remainingDouble =>
      double.tryParse(estimatedRemainingEntryAsset ?? '') ?? 0;

  factory BundleInvestPreviewResult.fromJson(Map<String, dynamic> json) {
    final rawAlloc = json['allocations'] as List<dynamic>? ?? [];
    final rawWarn = json['warnings'] as List<dynamic>? ?? [];
    return BundleInvestPreviewResult(
      previewStatus: json['preview_status'] as String? ?? 'invalid',
      bundleId: json['bundle_id'] as String?,
      bundleName: json['bundle_name'] as String?,
      fundingAsset: json['funding_asset'] as String?,
      fundingAmount: json['funding_amount']?.toString(),
      entryAssetUsed: json['entry_asset_used'] as String?,
      estimatedEntryAssetAmount:
          json['estimated_entry_asset_amount']?.toString(),
      estimatedRemainingEntryAsset:
          json['estimated_remaining_entry_asset']?.toString(),
      allocations: rawAlloc
          .map((e) =>
              BundlePreviewAllocation.fromJson(e as Map<String, dynamic>))
          .toList(),
      warnings: rawWarn.map((e) => e.toString()).toList(),
    );
  }
}

class BundlePreviewAllocation {
  const BundlePreviewAllocation({
    required this.asset,
    required this.targetWeight,
    required this.estimatedInputAmount,
    required this.estimatedOutputQuantity,
    required this.status,
  });

  final String asset;
  final String targetWeight;
  final String estimatedInputAmount;
  final String estimatedOutputQuantity;
  final String status;

  double get weightDouble => double.tryParse(targetWeight) ?? 0;
  double get inputDouble => double.tryParse(estimatedInputAmount) ?? 0;
  double get outputDouble => double.tryParse(estimatedOutputQuantity) ?? 0;
  String get percentLabel => '${(weightDouble * 100).toStringAsFixed(0)}%';
  bool get isOk => status == 'ok';

  factory BundlePreviewAllocation.fromJson(Map<String, dynamic> json) {
    return BundlePreviewAllocation(
      asset: json['asset'] as String? ?? '',
      targetWeight: json['target_weight']?.toString() ?? '0',
      estimatedInputAmount: json['estimated_input_amount']?.toString() ?? '0',
      estimatedOutputQuantity:
          json['estimated_output_quantity']?.toString() ?? '0',
      status: json['status'] as String? ?? 'unknown',
    );
  }
}

class MyBundleSummary {
  const MyBundleSummary({
    required this.portfolioId,
    required this.portfolioName,
    this.originProductId,
    required this.status,
    required this.assetsCount,
    required this.totalCostBasis,
    this.totalMarketValue,
    this.performancePct,
    required this.hasHoldings,
    required this.positions,
  });

  final String portfolioId;
  final String portfolioName;
  final String? originProductId;
  final String status;
  final int assetsCount;
  final double totalCostBasis;
  final double? totalMarketValue;
  final double? performancePct;
  final bool hasHoldings;
  final List<BundlePositionInfo> positions;

  List<BundlePositionInfo> get spotPositions =>
      positions.where((p) => p.positionType == 'spot').toList();

  factory MyBundleSummary.fromJson(Map<String, dynamic> json) {
    final rawPositions = json['positions'] as List<dynamic>? ?? [];
    return MyBundleSummary(
      portfolioId: json['portfolio_id'] as String? ?? '',
      portfolioName: json['portfolio_name'] as String? ?? '',
      originProductId: json['origin_product_id'] as String?,
      status: json['status'] as String? ?? '',
      assetsCount: json['assets_count'] as int? ?? 0,
      totalCostBasis: (json['total_cost_basis'] as num?)?.toDouble() ?? 0,
      totalMarketValue: (json['total_market_value'] as num?)?.toDouble(),
      performancePct: (json['performance_pct'] as num?)?.toDouble(),
      hasHoldings: json['has_holdings'] as bool? ?? false,
      positions: rawPositions
          .map((e) => BundlePositionInfo.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}

class BundleTransactionItem {
  const BundleTransactionItem({
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

  factory BundleTransactionItem.fromJson(Map<String, dynamic> json) {
    return BundleTransactionItem(
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
    );
  }
}

// ─── Rebalance models ───────────────────────────────────────────────

class RebalanceAllocationInfo {
  const RebalanceAllocationInfo({
    required this.asset,
    required this.currentValueEur,
    required this.currentWeightPct,
    required this.quantity,
  });

  final String asset;
  final double currentValueEur;
  final double currentWeightPct;
  final double quantity;

  factory RebalanceAllocationInfo.fromJson(Map<String, dynamic> json) {
    return RebalanceAllocationInfo(
      asset: json['asset'] as String? ?? '',
      currentValueEur: (json['current_value_eur'] as num?)?.toDouble() ?? 0,
      currentWeightPct: (json['current_weight_pct'] as num?)?.toDouble() ?? 0,
      quantity: (json['quantity'] as num?)?.toDouble() ?? 0,
    );
  }
}

class RebalanceTargetInfo {
  const RebalanceTargetInfo({
    required this.asset,
    required this.targetValueEur,
    required this.targetWeightPct,
    required this.deltaEur,
    required this.action,
  });

  final String asset;
  final double targetValueEur;
  final double targetWeightPct;
  final double deltaEur;
  final String action;

  factory RebalanceTargetInfo.fromJson(Map<String, dynamic> json) {
    return RebalanceTargetInfo(
      asset: json['asset'] as String? ?? '',
      targetValueEur: (json['target_value_eur'] as num?)?.toDouble() ?? 0,
      targetWeightPct: (json['target_weight_pct'] as num?)?.toDouble() ?? 0,
      deltaEur: (json['delta_eur'] as num?)?.toDouble() ?? 0,
      action: json['action'] as String? ?? 'hold',
    );
  }
}

class RebalanceTradePlan {
  const RebalanceTradePlan({
    required this.asset,
    required this.instrumentId,
    required this.estimatedValueEur,
    this.quantity,
    this.entryAssetAmount,
  });

  final String asset;
  final String instrumentId;
  final double estimatedValueEur;
  final double? quantity;
  final double? entryAssetAmount;

  factory RebalanceTradePlan.fromJson(Map<String, dynamic> json) {
    return RebalanceTradePlan(
      asset: json['asset'] as String? ?? '',
      instrumentId: json['instrument_id'] as String? ?? '',
      estimatedValueEur: (json['estimated_value_eur'] as num?)?.toDouble() ?? 0,
      quantity: (json['quantity'] as num?)?.toDouble(),
      entryAssetAmount: (json['entry_asset_amount'] as num?)?.toDouble(),
    );
  }
}

class RebalancePreviewResult {
  const RebalancePreviewResult({
    required this.portfolioId,
    required this.status,
    required this.baseValueEur,
    required this.cashLegValueEur,
    this.currentAllocations = const [],
    this.targetAllocations = const [],
    this.sellPlan = const [],
    this.buyPlan = const [],
    required this.estimatedResidualCashLeg,
    this.warnings = const [],
  });

  final String portfolioId;
  final String status;
  final double baseValueEur;
  final double cashLegValueEur;
  final List<RebalanceAllocationInfo> currentAllocations;
  final List<RebalanceTargetInfo> targetAllocations;
  final List<RebalanceTradePlan> sellPlan;
  final List<RebalanceTradePlan> buyPlan;
  final double estimatedResidualCashLeg;
  final List<String> warnings;

  bool get isOk => status == 'ok';
  bool get isNoAction => status == 'no_action';
  bool get isPartial => status == 'partial';
  bool get isInvalid => status == 'invalid';
  bool get hasActions => sellPlan.isNotEmpty || buyPlan.isNotEmpty;

  factory RebalancePreviewResult.fromJson(Map<String, dynamic> json) {
    return RebalancePreviewResult(
      portfolioId: json['portfolio_id'] as String? ?? '',
      status: json['status'] as String? ?? 'invalid',
      baseValueEur: (json['base_value_eur'] as num?)?.toDouble() ?? 0,
      cashLegValueEur: (json['cash_leg_value_eur'] as num?)?.toDouble() ?? 0,
      currentAllocations: (json['current_allocations'] as List<dynamic>? ?? [])
          .map((e) => RebalanceAllocationInfo.fromJson(e as Map<String, dynamic>))
          .toList(),
      targetAllocations: (json['target_allocations'] as List<dynamic>? ?? [])
          .map((e) => RebalanceTargetInfo.fromJson(e as Map<String, dynamic>))
          .toList(),
      sellPlan: (json['sell_plan'] as List<dynamic>? ?? [])
          .map((e) => RebalanceTradePlan.fromJson(e as Map<String, dynamic>))
          .toList(),
      buyPlan: (json['buy_plan'] as List<dynamic>? ?? [])
          .map((e) => RebalanceTradePlan.fromJson(e as Map<String, dynamic>))
          .toList(),
      estimatedResidualCashLeg:
          (json['estimated_residual_cash_leg'] as num?)?.toDouble() ?? 0,
      warnings: (json['warnings'] as List<dynamic>? ?? [])
          .map((e) => e.toString())
          .toList(),
    );
  }
}

class RebalanceTradeResult {
  const RebalanceTradeResult({
    required this.asset,
    required this.valueEur,
    required this.status,
    this.quantitySold,
    this.quantityBought,
    this.entryAssetReceived,
    this.entryAssetSpent,
    this.error,
  });

  final String asset;
  final double valueEur;
  final String status;
  final double? quantitySold;
  final double? quantityBought;
  final double? entryAssetReceived;
  final double? entryAssetSpent;
  final String? error;

  bool get isCompleted => status == 'completed';

  factory RebalanceTradeResult.fromJson(Map<String, dynamic> json) {
    return RebalanceTradeResult(
      asset: json['asset'] as String? ?? '',
      valueEur: (json['value_eur'] as num?)?.toDouble() ?? 0,
      status: json['status'] as String? ?? 'unknown',
      quantitySold: (json['quantity_sold'] as num?)?.toDouble(),
      quantityBought: (json['quantity_bought'] as num?)?.toDouble(),
      entryAssetReceived: (json['entry_asset_received'] as num?)?.toDouble(),
      entryAssetSpent: (json['entry_asset_spent'] as num?)?.toDouble(),
      error: json['error'] as String?,
    );
  }
}

class RebalanceExecuteResult {
  const RebalanceExecuteResult({
    required this.portfolioId,
    required this.status,
    this.batchId,
    this.sellResults = const [],
    this.buyResults = const [],
    required this.cashLegBefore,
    required this.cashLegAfter,
    this.message,
  });

  final String portfolioId;
  final String status;
  final String? batchId;
  final List<RebalanceTradeResult> sellResults;
  final List<RebalanceTradeResult> buyResults;
  final double cashLegBefore;
  final double cashLegAfter;
  final String? message;

  bool get isCompleted => status == 'completed';
  bool get isPartial => status == 'partial';
  bool get isFailed => status == 'failed';
  bool get isNoAction => status == 'no_action';
  bool get isSuccess => isCompleted || isPartial;

  int get sellsCompleted => sellResults.where((r) => r.isCompleted).length;
  int get buysCompleted => buyResults.where((r) => r.isCompleted).length;
  int get totalTrades => sellResults.length + buyResults.length;
  int get totalCompleted => sellsCompleted + buysCompleted;

  factory RebalanceExecuteResult.fromJson(Map<String, dynamic> json) {
    return RebalanceExecuteResult(
      portfolioId: json['portfolio_id'] as String? ?? '',
      status: json['status'] as String? ?? 'failed',
      batchId: json['batch_id'] as String?,
      sellResults: (json['sell_results'] as List<dynamic>? ?? [])
          .map((e) => RebalanceTradeResult.fromJson(e as Map<String, dynamic>))
          .toList(),
      buyResults: (json['buy_results'] as List<dynamic>? ?? [])
          .map((e) => RebalanceTradeResult.fromJson(e as Map<String, dynamic>))
          .toList(),
      cashLegBefore: (json['cash_leg_before'] as num?)?.toDouble() ?? 0,
      cashLegAfter: (json['cash_leg_after'] as num?)?.toDouble() ?? 0,
      message: json['message'] as String?,
    );
  }
}

// ─── Bundle portfolio-level statistics ───────────────────────────

class AllocationVsTarget {
  const AllocationVsTarget({
    required this.asset,
    required this.targetPct,
    required this.currentPct,
    required this.driftPct,
  });

  final String asset;
  final double targetPct;
  final double currentPct;
  final double driftPct;

  factory AllocationVsTarget.fromJson(Map<String, dynamic> json) {
    return AllocationVsTarget(
      asset: json['asset'] as String? ?? '',
      targetPct: (json['target_pct'] as num?)?.toDouble() ?? 0,
      currentPct: (json['current_pct'] as num?)?.toDouble() ?? 0,
      driftPct: (json['drift_pct'] as num?)?.toDouble() ?? 0,
    );
  }
}

class AssetContribution {
  const AssetContribution({
    required this.asset,
    required this.pnl,
    required this.contributionPct,
  });

  final String asset;
  final double pnl;
  final double contributionPct;

  factory AssetContribution.fromJson(Map<String, dynamic> json) {
    return AssetContribution(
      asset: json['asset'] as String? ?? '',
      pnl: (json['pnl'] as num?)?.toDouble() ?? 0,
      contributionPct: (json['contribution_pct'] as num?)?.toDouble() ?? 0,
    );
  }
}

class BundlePortfolioStatistics {
  const BundlePortfolioStatistics({
    required this.portfolioId,
    required this.portfolioName,
    required this.currentValue,
    required this.totalInvested,
    required this.totalPnl,
    required this.performancePct,
    required this.allocationVsTarget,
    required this.contributions,
    required this.investedPct,
    required this.cashPct,
    required this.cashValue,
    required this.rebalanceCount,
    required this.totalAllocationEvents,
    required this.assetsCount,
    this.concentrationAsset,
    required this.concentrationPct,
  });

  final String portfolioId;
  final String portfolioName;
  final double currentValue;
  final double totalInvested;
  final double totalPnl;
  final double performancePct;
  final List<AllocationVsTarget> allocationVsTarget;
  final List<AssetContribution> contributions;
  final double investedPct;
  final double cashPct;
  final double cashValue;
  final int rebalanceCount;
  final int totalAllocationEvents;
  final int assetsCount;
  final String? concentrationAsset;
  final double concentrationPct;

  factory BundlePortfolioStatistics.fromJson(Map<String, dynamic> json) {
    final perf = json['performance'] as Map<String, dynamic>? ?? {};
    final cash = json['cash_deployment'] as Map<String, dynamic>? ?? {};
    final activity = json['activity'] as Map<String, dynamic>? ?? {};
    final risk = json['risk'] as Map<String, dynamic>? ?? {};
    final rawAlloc = json['allocation_vs_target'] as List<dynamic>? ?? [];
    final rawContrib = json['contributions'] as List<dynamic>? ?? [];

    return BundlePortfolioStatistics(
      portfolioId: json['portfolio_id'] as String? ?? '',
      portfolioName: json['portfolio_name'] as String? ?? '',
      currentValue: (perf['current_value'] as num?)?.toDouble() ?? 0,
      totalInvested: (perf['total_invested'] as num?)?.toDouble() ?? 0,
      totalPnl: (perf['total_pnl'] as num?)?.toDouble() ?? 0,
      performancePct: (perf['performance_pct'] as num?)?.toDouble() ?? 0,
      allocationVsTarget: rawAlloc
          .map((e) => AllocationVsTarget.fromJson(e as Map<String, dynamic>))
          .toList(),
      contributions: rawContrib
          .map((e) => AssetContribution.fromJson(e as Map<String, dynamic>))
          .toList(),
      investedPct: (cash['invested_pct'] as num?)?.toDouble() ?? 0,
      cashPct: (cash['cash_pct'] as num?)?.toDouble() ?? 0,
      cashValue: (cash['cash_value'] as num?)?.toDouble() ?? 0,
      rebalanceCount: activity['rebalance_count'] as int? ?? 0,
      totalAllocationEvents: activity['total_allocation_events'] as int? ?? 0,
      assetsCount: risk['assets_count'] as int? ?? 0,
      concentrationAsset: risk['concentration_asset'] as String?,
      concentrationPct: (risk['concentration_pct'] as num?)?.toDouble() ?? 0,
    );
  }
}

class BundleApi {
  const BundleApi();

  Future<Map<String, String>> _jsonHeaders(Uri uri, String tag) =>
      SessionBearerHttp.jsonHeadersAppScoped(
        uri: uri,
        debugTag: tag,
        withJsonContentType: true,
      );

  Future<List<MyBundleSummary>> getMyBundles() async {
    final uri = Uri.parse(Config.myBundlesUrl);
    final response = await http.get(
      uri,
      headers: await _jsonHeaders(uri, 'BundleApi.getMyBundles'),
    );

    if (response.statusCode >= 400) {
      throw ExchangeApiException(
        'my_bundles_error',
        statusCode: response.statusCode,
      );
    }

    final json = jsonDecode(response.body) as Map<String, dynamic>;
    final rawBundles = json['bundles'] as List<dynamic>? ?? [];
    return rawBundles
        .map((e) => MyBundleSummary.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<BundleInvestPreviewResult> previewBundleInvestment({
    required String portfolioId,
    required String fundingAsset,
    required double fundingAmount,
  }) async {
    final uri = Uri.parse(Config.bundleInvestPreviewUrl);
    final response = await http.post(
      uri,
      headers: await _jsonHeaders(uri, 'BundleApi.previewBundleInvestment'),
      body: jsonEncode({
        'portfolio_id': portfolioId,
        'funding_asset': fundingAsset,
        'funding_amount': fundingAmount,
      }),
    );

    final json = jsonDecode(response.body) as Map<String, dynamic>;

    if (response.statusCode >= 400) {
      final detail = json['detail'];
      if (detail is String) {
        throw ExchangeApiException(
          detail,
          statusCode: response.statusCode,
          errorCode: detail,
        );
      }
      throw ExchangeApiException(
        detail?.toString() ?? 'bundle_preview_error',
        statusCode: response.statusCode,
        errorCode: 'BUNDLE_PREVIEW_ERROR',
      );
    }

    return BundleInvestPreviewResult.fromJson(json);
  }

  Future<BundleInvestResult> investInBundle({
    required String portfolioId,
    required String fundingAsset,
    required double fundingAmount,
  }) async {
    final uri = Uri.parse(Config.bundleInvestUrl);
    final response = await http.post(
      uri,
      headers: await _jsonHeaders(uri, 'BundleApi.investInBundle'),
      body: jsonEncode({
        'portfolio_id': portfolioId,
        'funding_asset': fundingAsset,
        'funding_amount': fundingAmount,
      }),
    );

    final json = jsonDecode(response.body) as Map<String, dynamic>;

    if (response.statusCode >= 400) {
      final detail = json['detail'];
      if (detail is String) {
        throw ExchangeApiException(
          detail,
          statusCode: response.statusCode,
          errorCode: detail,
        );
      }
      throw ExchangeApiException(
        detail?.toString() ?? 'bundle_invest_error',
        statusCode: response.statusCode,
        errorCode: 'BUNDLE_ERROR',
      );
    }

    return BundleInvestResult.fromJson(json);
  }

  Future<List<BundleTransactionItem>> getBundleTransactions({
    required String portfolioId,
  }) async {
    final uri = Uri.parse(Config.bundleTransactionsUrl(portfolioId));
    final response = await http.get(
      uri,
      headers: await _jsonHeaders(uri, 'BundleApi.getBundleTransactions'),
    );

    if (response.statusCode >= 400) {
      throw ExchangeApiException(
        'bundle_transactions_error',
        statusCode: response.statusCode,
      );
    }

    final json = jsonDecode(response.body) as Map<String, dynamic>;
    final list = json['transactions'] as List<dynamic>? ?? [];
    return list
        .map((e) => BundleTransactionItem.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<BundleStatusResult> getBundleStatus({
    required String portfolioId,
  }) async {
    final uri = Uri.parse(Config.bundleStatusUrl(portfolioId));
    final response = await http.get(
      uri,
      headers: await _jsonHeaders(uri, 'BundleApi.getBundleStatus'),
    );

    final json = jsonDecode(response.body) as Map<String, dynamic>;

    if (response.statusCode >= 400) {
      throw ExchangeApiException(
        json['detail']?.toString() ?? 'bundle_status_error',
        statusCode: response.statusCode,
      );
    }

    return BundleStatusResult.fromJson(json);
  }

  Future<BundlePortfolioStatistics> getBundlePortfolioStatistics({
    required String portfolioId,
  }) async {
    final uri = Uri.parse(Config.bundleStatisticsUrl(portfolioId));
    final response = await http.get(
      uri,
      headers: await _jsonHeaders(uri, 'BundleApi.getBundlePortfolioStatistics'),
    );

    if (response.statusCode >= 400) {
      throw ExchangeApiException(
        'bundle_statistics_error',
        statusCode: response.statusCode,
      );
    }

    final json = jsonDecode(response.body) as Map<String, dynamic>;
    return BundlePortfolioStatistics.fromJson(json);
  }

  Future<RebalancePreviewResult> previewRebalance({
    required String portfolioId,
  }) async {
    final uri = Uri.parse(Config.bundleRebalancePreviewUrl(portfolioId));
    final response = await http.post(
      uri,
      headers: await _jsonHeaders(uri, 'BundleApi.previewRebalance'),
    );

    final json = jsonDecode(response.body) as Map<String, dynamic>;

    if (response.statusCode >= 400) {
      final detail = json['detail'];
      throw ExchangeApiException(
        detail?.toString() ?? 'rebalance_preview_error',
        statusCode: response.statusCode,
        errorCode: detail is String ? detail : 'REBALANCE_PREVIEW_ERROR',
      );
    }

    return RebalancePreviewResult.fromJson(json);
  }

  Future<RebalanceExecuteResult> executeRebalance({
    required String portfolioId,
  }) async {
    final uri = Uri.parse(Config.bundleRebalanceExecuteUrl(portfolioId));
    final response = await http.post(
      uri,
      headers: await _jsonHeaders(uri, 'BundleApi.executeRebalance'),
    );

    final json = jsonDecode(response.body) as Map<String, dynamic>;

    if (response.statusCode >= 400) {
      final detail = json['detail'];
      throw ExchangeApiException(
        detail?.toString() ?? 'rebalance_error',
        statusCode: response.statusCode,
        errorCode: detail is String ? detail : 'REBALANCE_ERROR',
      );
    }

    return RebalanceExecuteResult.fromJson(json);
  }
}
