import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../core/config.dart';
import '../../../core/session_bearer_http.dart';

class BuyPreviewResult {
  const BuyPreviewResult({
    required this.asset,
    required this.amountFiat,
    required this.estimatedPrice,
    required this.estimatedCryptoGross,
    required this.feeAmount,
    required this.feeAsset,
    required this.feeBps,
    required this.estimatedCryptoNet,
    required this.currency,
    required this.isFresh,
    this.error,
  });

  final String asset;
  final double amountFiat;
  final double estimatedPrice;
  final double estimatedCryptoGross;
  final double feeAmount;
  final String feeAsset;
  final int feeBps;
  final double estimatedCryptoNet;
  final String currency;
  final bool isFresh;
  final String? error;

  bool get hasError => error != null;

  factory BuyPreviewResult.fromJson(Map<String, dynamic> json) {
    if (json.containsKey('error') || json.containsKey('error_code')) {
      return BuyPreviewResult(
        asset: json['asset'] as String? ?? '',
        amountFiat: 0,
        estimatedPrice: 0,
        estimatedCryptoGross: 0,
        feeAmount: 0,
        feeAsset: '',
        feeBps: 0,
        estimatedCryptoNet: 0,
        currency: '',
        isFresh: json['is_fresh'] as bool? ?? false,
        error: json['error_code'] as String? ?? json['error'] as String?,
      );
    }
    return BuyPreviewResult(
      asset: json['asset'] as String? ?? '',
      amountFiat: (json['amount_fiat'] as num?)?.toDouble() ?? 0,
      estimatedPrice: (json['estimated_price'] as num?)?.toDouble() ?? 0,
      estimatedCryptoGross: (json['estimated_crypto_gross'] as num?)?.toDouble() ?? 0,
      feeAmount: (json['fee_amount'] as num?)?.toDouble() ?? 0,
      feeAsset: json['fee_asset'] as String? ?? '',
      feeBps: (json['fee_bps'] as num?)?.toInt() ?? 0,
      estimatedCryptoNet: (json['estimated_crypto_net'] as num?)?.toDouble() ?? 0,
      currency: json['currency'] as String? ?? 'EUR',
      isFresh: json['is_fresh'] as bool? ?? true,
    );
  }
}

class BuyResult {
  const BuyResult({
    required this.status,
    this.orderId,
    this.asset,
    this.amountCrypto,
    this.amountFiat,
    this.price,
    this.feeAmount,
    this.feeAsset,
    this.errorCode,
    this.message,
  });

  final String status;
  final String? orderId;
  final String? asset;
  final double? amountCrypto;
  final double? amountFiat;
  final double? price;
  final double? feeAmount;
  final String? feeAsset;
  final String? errorCode;
  final String? message;

  bool get isSuccess => status == 'completed';
  bool get isFailed => status == 'failed';

  factory BuyResult.fromJson(Map<String, dynamic> json) {
    return BuyResult(
      status: json['status'] as String? ?? 'failed',
      orderId: json['order_id']?.toString(),
      asset: json['asset'] as String?,
      amountCrypto: _num(json['amount_crypto'] ?? json['amount_to']),
      amountFiat: _num(json['amount_fiat'] ?? json['amount_from']),
      price: _num(json['price']),
      feeAmount: _num(json['fee_amount']),
      feeAsset: json['fee_asset'] as String?,
      errorCode: json['error_code'] as String? ?? json['error'] as String?,
      message: json['message'] as String?,
    );
  }

  static double? _num(dynamic v) {
    if (v == null) return null;
    return double.tryParse(v.toString());
  }
}

class SellPreviewResult {
  const SellPreviewResult({
    required this.asset,
    required this.amountCrypto,
    required this.estimatedPrice,
    required this.estimatedFiatGross,
    required this.feeAmount,
    required this.feeAsset,
    required this.feeBps,
    required this.estimatedFiatNet,
    required this.currency,
    required this.isFresh,
    this.error,
  });

  final String asset;
  final double amountCrypto;
  final double estimatedPrice;
  final double estimatedFiatGross;
  final double feeAmount;
  final String feeAsset;
  final int feeBps;
  final double estimatedFiatNet;
  final String currency;
  final bool isFresh;
  final String? error;

  bool get hasError => error != null;

  factory SellPreviewResult.fromJson(Map<String, dynamic> json) {
    if (json.containsKey('error') || json.containsKey('error_code')) {
      return SellPreviewResult(
        asset: json['asset'] as String? ?? '',
        amountCrypto: 0,
        estimatedPrice: 0,
        estimatedFiatGross: 0,
        feeAmount: 0,
        feeAsset: '',
        feeBps: 0,
        estimatedFiatNet: 0,
        currency: '',
        isFresh: json['is_fresh'] as bool? ?? false,
        error: json['error_code'] as String? ?? json['error'] as String?,
      );
    }
    return SellPreviewResult(
      asset: json['asset'] as String? ?? '',
      amountCrypto: (json['amount_crypto'] as num?)?.toDouble() ?? 0,
      estimatedPrice: (json['estimated_price'] as num?)?.toDouble() ?? 0,
      estimatedFiatGross: (json['estimated_fiat_gross'] as num?)?.toDouble() ?? 0,
      feeAmount: (json['fee_amount'] as num?)?.toDouble() ?? 0,
      feeAsset: json['fee_asset'] as String? ?? '',
      feeBps: (json['fee_bps'] as num?)?.toInt() ?? 0,
      estimatedFiatNet: (json['estimated_fiat_net'] as num?)?.toDouble() ?? 0,
      currency: json['currency'] as String? ?? 'EUR',
      isFresh: json['is_fresh'] as bool? ?? true,
    );
  }
}

class SellResult {
  const SellResult({
    required this.status,
    this.orderId,
    this.asset,
    this.amountCrypto,
    this.amountFiat,
    this.price,
    this.feeAmount,
    this.feeAsset,
    this.errorCode,
    this.message,
  });

  final String status;
  final String? orderId;
  final String? asset;
  final double? amountCrypto;
  final double? amountFiat;
  final double? price;
  final double? feeAmount;
  final String? feeAsset;
  final String? errorCode;
  final String? message;

  bool get isSuccess => status == 'completed';
  bool get isFailed => status == 'failed';

  factory SellResult.fromJson(Map<String, dynamic> json) {
    return SellResult(
      status: json['status'] as String? ?? 'failed',
      orderId: json['order_id']?.toString(),
      asset: json['asset'] as String?,
      amountCrypto: BuyResult._num(json['amount_crypto'] ?? json['amount_from']),
      amountFiat: BuyResult._num(json['amount_fiat'] ?? json['amount_to'] ?? json['net_eur']),
      price: BuyResult._num(json['price'] ?? json['price_eur']),
      feeAmount: BuyResult._num(json['fee_amount'] ?? json['fee_eur']),
      feeAsset: json['fee_asset'] as String?,
      errorCode: json['error_code'] as String? ?? json['error'] as String?,
      message: json['message'] as String?,
    );
  }
}

class SwapPreviewResult {
  const SwapPreviewResult({
    required this.fromAsset,
    required this.toAsset,
    required this.amountFrom,
    required this.estimatedRefValueGross,
    required this.feeInRefCurrency,
    required this.estimatedRefValueNet,
    required this.estimatedToAmount,
    required this.fromPrice,
    required this.toPrice,
    required this.referenceCurrency,
    required this.isFresh,
    this.error,
  });

  final String fromAsset;
  final String toAsset;
  final double amountFrom;
  final double estimatedRefValueGross;
  final double feeInRefCurrency;
  final double estimatedRefValueNet;
  final double estimatedToAmount;
  final double fromPrice;
  final double toPrice;
  final String referenceCurrency;
  final bool isFresh;
  final String? error;

  bool get hasError => error != null;

  factory SwapPreviewResult.fromJson(Map<String, dynamic> json) {
    if (json.containsKey('error') || json.containsKey('error_code')) {
      return SwapPreviewResult(
        fromAsset: json['from_asset'] as String? ?? '',
        toAsset: json['to_asset'] as String? ?? '',
        amountFrom: 0,
        estimatedRefValueGross: 0,
        feeInRefCurrency: 0,
        estimatedRefValueNet: 0,
        estimatedToAmount: 0,
        fromPrice: 0,
        toPrice: 0,
        referenceCurrency: '',
        isFresh: false,
        error: json['error_code'] as String? ?? json['error'] as String?,
      );
    }
    return SwapPreviewResult(
      fromAsset: json['from_asset'] as String? ?? '',
      toAsset: json['to_asset'] as String? ?? '',
      amountFrom: (json['amount_from'] as num?)?.toDouble() ?? 0,
      estimatedRefValueGross: (json['estimated_reference_value_gross'] as num?)?.toDouble() ?? 0,
      feeInRefCurrency: (json['fee_in_reference_currency'] as num?)?.toDouble() ?? 0,
      estimatedRefValueNet: (json['estimated_reference_value_net'] as num?)?.toDouble() ?? 0,
      estimatedToAmount: (json['estimated_to_amount'] as num?)?.toDouble() ?? 0,
      fromPrice: (json['from_price_in_ref_ccy'] as num?)?.toDouble() ?? 0,
      toPrice: (json['to_price_in_ref_ccy'] as num?)?.toDouble() ?? 0,
      referenceCurrency: json['reference_currency'] as String? ?? 'EUR',
      isFresh: json['is_fresh'] as bool? ?? true,
    );
  }
}

class SwapResult {
  const SwapResult({
    required this.status,
    this.swapGroupId,
    this.fromAsset,
    this.toAsset,
    this.amountFrom,
    this.amountTo,
    this.referenceValueNet,
    this.feeInRefCurrency,
    this.errorCode,
    this.message,
  });

  final String status;
  final String? swapGroupId;
  final String? fromAsset;
  final String? toAsset;
  final double? amountFrom;
  final double? amountTo;
  final double? referenceValueNet;
  final double? feeInRefCurrency;
  final String? errorCode;
  final String? message;

  bool get isSuccess => status == 'completed';
  bool get isFailed => status == 'failed';

  factory SwapResult.fromJson(Map<String, dynamic> json) {
    return SwapResult(
      status: json['status'] as String? ?? 'failed',
      swapGroupId: json['swap_group_id']?.toString(),
      fromAsset: json['from_asset'] as String?,
      toAsset: json['to_asset'] as String?,
      amountFrom: BuyResult._num(json['amount_from']),
      amountTo: BuyResult._num(json['amount_to']),
      referenceValueNet: BuyResult._num(json['reference_value_net']),
      feeInRefCurrency: BuyResult._num(json['fee_in_reference_currency']),
      errorCode: json['error_code'] as String? ?? json['error'] as String?,
      message: json['message'] as String?,
    );
  }
}

/// Achat / vente / swap euro↔crypto : BFF `/api/mobile/flutter/exchange/*` avec JWT
/// ([jsonHeadersAppScoped]) — le client PE est résolu côté API à partir du token.
class ExchangeApi {
  const ExchangeApi();

  Future<Map<String, String>> _jsonHeaders(Uri uri, String tag) =>
      SessionBearerHttp.jsonHeadersAppScoped(
        uri: uri,
        debugTag: tag,
        withJsonContentType: true,
      );

  Future<BuyPreviewResult> previewBuy({
    required String asset,
    required double amountFiat,
  }) async {
    final uri = Uri.parse(Config.exchangeBuyPreviewUrl);
    final response = await http.post(
      uri,
      headers: await _jsonHeaders(uri, 'ExchangeApi.previewBuy'),
      body: jsonEncode({'asset': asset, 'amount_fiat': amountFiat}),
    );

    final json = jsonDecode(response.body) as Map<String, dynamic>;

    if (response.statusCode >= 400) {
      final detail = json['detail'];
      if (detail is Map<String, dynamic>) {
        return BuyPreviewResult.fromJson(detail);
      }
      throw ExchangeApiException(
        detail?.toString() ?? 'preview_error',
        statusCode: response.statusCode,
        errorCode: 'PREVIEW_ERROR',
      );
    }

    return BuyPreviewResult.fromJson(json);
  }

  Future<BuyResult> executeBuy({
    required String asset,
    required double amountFiat,
  }) async {
    final uri = Uri.parse(Config.exchangeBuyUrl);
    final response = await http.post(
      uri,
      headers: await _jsonHeaders(uri, 'ExchangeApi.executeBuy'),
      body: jsonEncode({'asset': asset, 'amount_fiat': amountFiat}),
    );

    final json = jsonDecode(response.body) as Map<String, dynamic>;

    if (response.statusCode >= 400) {
      final detail = json['detail'];
      if (detail is Map<String, dynamic>) {
        return BuyResult.fromJson(detail);
      }
      throw ExchangeApiException(
        detail?.toString() ?? 'buy_error',
        statusCode: response.statusCode,
        errorCode: _codeFromStatus(response.statusCode),
      );
    }

    return BuyResult.fromJson(json);
  }

  Future<SellPreviewResult> previewSell({
    required String asset,
    required double amountCrypto,
  }) async {
    final uri = Uri.parse(Config.exchangeSellPreviewUrl);
    final response = await http.post(
      uri,
      headers: await _jsonHeaders(uri, 'ExchangeApi.previewSell'),
      body: jsonEncode({'asset': asset, 'amount_crypto': amountCrypto}),
    );

    final json = jsonDecode(response.body) as Map<String, dynamic>;

    if (response.statusCode >= 400) {
      final detail = json['detail'];
      if (detail is Map<String, dynamic>) {
        return SellPreviewResult.fromJson(detail);
      }
      throw ExchangeApiException(
        detail?.toString() ?? 'preview_error',
        statusCode: response.statusCode,
        errorCode: 'PREVIEW_ERROR',
      );
    }

    return SellPreviewResult.fromJson(json);
  }

  Future<SellResult> executeSell({
    required String asset,
    required double amountCrypto,
  }) async {
    final uri = Uri.parse(Config.exchangeSellUrl);
    final response = await http.post(
      uri,
      headers: await _jsonHeaders(uri, 'ExchangeApi.executeSell'),
      body: jsonEncode({'asset': asset, 'amount_crypto': amountCrypto}),
    );

    final json = jsonDecode(response.body) as Map<String, dynamic>;

    if (response.statusCode >= 400) {
      final detail = json['detail'];
      if (detail is Map<String, dynamic>) {
        return SellResult.fromJson(detail);
      }
      throw ExchangeApiException(
        detail?.toString() ?? 'sell_error',
        statusCode: response.statusCode,
        errorCode: _codeFromStatus(response.statusCode),
      );
    }

    return SellResult.fromJson(json);
  }

  Future<SwapPreviewResult> previewSwap({
    required String fromAsset,
    required String toAsset,
    required double amountFrom,
  }) async {
    final uri = Uri.parse(Config.exchangeSwapPreviewUrl);
    final response = await http.post(
      uri,
      headers: await _jsonHeaders(uri, 'ExchangeApi.previewSwap'),
      body: jsonEncode({
        'from_asset': fromAsset,
        'to_asset': toAsset,
        'amount_from': amountFrom,
      }),
    );

    final json = jsonDecode(response.body) as Map<String, dynamic>;

    if (response.statusCode >= 400) {
      final detail = json['detail'];
      if (detail is Map<String, dynamic>) {
        return SwapPreviewResult.fromJson(detail);
      }
      throw ExchangeApiException(
        detail?.toString() ?? 'preview_error',
        statusCode: response.statusCode,
        errorCode: 'PREVIEW_ERROR',
      );
    }

    return SwapPreviewResult.fromJson(json);
  }

  Future<SwapResult> executeSwap({
    required String fromAsset,
    required String toAsset,
    required double amountFrom,
  }) async {
    final uri = Uri.parse(Config.exchangeSwapUrl);
    final response = await http.post(
      uri,
      headers: await _jsonHeaders(uri, 'ExchangeApi.executeSwap'),
      body: jsonEncode({
        'from_asset': fromAsset,
        'to_asset': toAsset,
        'amount_from': amountFrom,
      }),
    );

    final json = jsonDecode(response.body) as Map<String, dynamic>;

    if (response.statusCode >= 400) {
      final detail = json['detail'];
      if (detail is Map<String, dynamic>) {
        return SwapResult.fromJson(detail);
      }
      throw ExchangeApiException(
        detail?.toString() ?? 'swap_error',
        statusCode: response.statusCode,
        errorCode: _codeFromStatus(response.statusCode),
      );
    }

    return SwapResult.fromJson(json);
  }

  static String _codeFromStatus(int status) {
    if (status == 409) return 'CONFLICT';
    if (status == 503) return 'MARKET_UNAVAILABLE';
    if (status == 404) return 'NOT_FOUND';
    return 'EXCHANGE_ERROR';
  }
}

// ---------------------------------------------------------------------------
// Sell-all models
// ---------------------------------------------------------------------------

class SellAllPreviewItem {
  final String asset;
  final String amountAvailable;
  final double estimatedEurNet;
  final double estimatedEurGross;
  final double feeAmount;
  final double price;
  final String status;
  final String? errorCode;
  final String? errorMessage;

  const SellAllPreviewItem({
    required this.asset,
    required this.amountAvailable,
    required this.estimatedEurNet,
    required this.estimatedEurGross,
    required this.feeAmount,
    required this.price,
    required this.status,
    this.errorCode,
    this.errorMessage,
  });

  factory SellAllPreviewItem.fromJson(Map<String, dynamic> json) {
    return SellAllPreviewItem(
      asset: json['asset'] as String? ?? '',
      amountAvailable: json['amount_available']?.toString() ?? '0',
      estimatedEurNet: (json['estimated_eur_net'] as num?)?.toDouble() ?? 0,
      estimatedEurGross: (json['estimated_eur_gross'] as num?)?.toDouble() ?? 0,
      feeAmount: (json['fee_amount'] as num?)?.toDouble() ?? 0,
      price: (json['price'] as num?)?.toDouble() ?? 0,
      status: json['status'] as String? ?? 'unknown',
      errorCode: json['error_code'] as String?,
      errorMessage: json['error_message'] as String?,
    );
  }

  bool get isReady => status == 'ready';
}

class SellAllPreviewResult {
  final int totalAssets;
  final double estimatedTotalEur;
  final List<SellAllPreviewItem> items;
  final String? error;

  const SellAllPreviewResult({
    required this.totalAssets,
    required this.estimatedTotalEur,
    required this.items,
    this.error,
  });

  factory SellAllPreviewResult.fromJson(Map<String, dynamic> json) {
    final rawItems = json['items'] as List<dynamic>? ?? [];
    return SellAllPreviewResult(
      totalAssets: (json['total_assets'] as int?) ?? 0,
      estimatedTotalEur: (json['estimated_total_eur'] as num?)?.toDouble() ?? 0,
      items: rawItems
          .map((e) => SellAllPreviewItem.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}

class SellAllResultItem {
  final String asset;
  final String status;
  final String? amountSold;
  final String? eurReceived;
  final String? orderId;
  final String? realizedPnl;
  final String? errorCode;
  final String? errorMessage;

  const SellAllResultItem({
    required this.asset,
    required this.status,
    this.amountSold,
    this.eurReceived,
    this.orderId,
    this.realizedPnl,
    this.errorCode,
    this.errorMessage,
  });

  factory SellAllResultItem.fromJson(Map<String, dynamic> json) {
    return SellAllResultItem(
      asset: json['asset'] as String? ?? '',
      status: json['status'] as String? ?? 'unknown',
      amountSold: json['amount_sold'] as String?,
      eurReceived: json['eur_received'] as String?,
      orderId: json['order_id'] as String?,
      realizedPnl: json['realized_pnl'] as String?,
      errorCode: json['error_code'] as String?,
      errorMessage: json['error_message'] as String?,
    );
  }

  bool get isCompleted => status == 'completed';
}

class SellAllResult {
  final String status;
  final String batchId;
  final int totalAssetsDetected;
  final int totalAssetsSold;
  final int totalAssetsFailed;
  final double estimatedTotalEurBefore;
  final double actualTotalEurReceived;
  final List<SellAllResultItem> results;

  const SellAllResult({
    required this.status,
    required this.batchId,
    required this.totalAssetsDetected,
    required this.totalAssetsSold,
    required this.totalAssetsFailed,
    required this.estimatedTotalEurBefore,
    required this.actualTotalEurReceived,
    required this.results,
  });

  factory SellAllResult.fromJson(Map<String, dynamic> json) {
    final rawResults = json['results'] as List<dynamic>? ?? [];
    return SellAllResult(
      status: json['status'] as String? ?? 'unknown',
      batchId: json['batch_id'] as String? ?? '',
      totalAssetsDetected: (json['total_assets_detected'] as int?) ?? 0,
      totalAssetsSold: (json['total_assets_sold'] as int?) ?? 0,
      totalAssetsFailed: (json['total_assets_failed'] as int?) ?? 0,
      estimatedTotalEurBefore: (json['estimated_total_eur_before'] as num?)?.toDouble() ?? 0,
      actualTotalEurReceived: (json['actual_total_eur_received'] as num?)?.toDouble() ?? 0,
      results: rawResults
          .map((e) => SellAllResultItem.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}

// ---------------------------------------------------------------------------
// ExchangeApi extensions for sell-all (keep at bottom of file before Exception)
// ---------------------------------------------------------------------------

extension ExchangeApiSellAll on ExchangeApi {
  Future<SellAllPreviewResult> previewSellAll() async {
    final url = Uri.parse(Config.exchangeSellAllPreviewUrl);
    final response = await http.post(
      url,
      headers: await SessionBearerHttp.jsonHeadersAppScoped(
        uri: url,
        debugTag: 'ExchangeApi.previewSellAll',
        withJsonContentType: true,
      ),
    );
    final json = jsonDecode(response.body) as Map<String, dynamic>;

    if (response.statusCode != 200) {
      return SellAllPreviewResult(
        totalAssets: 0,
        estimatedTotalEur: 0,
        items: [],
        error: json['error']?.toString() ?? json['detail']?.toString() ?? 'preview_error',
      );
    }
    return SellAllPreviewResult.fromJson(json);
  }

  Future<SellAllResult> executeSellAll() async {
    final url = Uri.parse(Config.exchangeSellAllUrl);
    final response = await http.post(
      url,
      headers: await SessionBearerHttp.jsonHeadersAppScoped(
        uri: url,
        debugTag: 'ExchangeApi.executeSellAll',
        withJsonContentType: true,
      ),
    );
    final json = jsonDecode(response.body) as Map<String, dynamic>;

    if (response.statusCode != 200) {
      throw ExchangeApiException(
        json['detail']?.toString() ?? 'sell_all_error',
        statusCode: response.statusCode,
      );
    }
    return SellAllResult.fromJson(json);
  }
}

class ExchangeApiException implements Exception {
  final String message;
  final int? statusCode;
  final String? errorCode;
  const ExchangeApiException(this.message, {this.statusCode, this.errorCode});

  @override
  String toString() => 'ExchangeApiException($statusCode/$errorCode): $message';
}
