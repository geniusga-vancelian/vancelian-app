import 'dart:convert';

import 'package:http/http.dart' as http;

import '../../../core/config.dart';
import '../../../core/session_bearer_http.dart';

class LifiSwapAsset {
  const LifiSwapAsset({
    required this.symbol,
    required this.displayName,
    required this.chains,
    required this.minAmount,
    required this.maxAmount,
  });

  final String symbol;
  final String displayName;
  final List<String> chains;
  final String minAmount;
  final String maxAmount;

  factory LifiSwapAsset.fromJson(Map<String, dynamic> json) {
    return LifiSwapAsset(
      symbol: json['symbol'] as String? ?? '',
      displayName: json['display_name'] as String? ?? '',
      chains: (json['chains'] as List<dynamic>? ?? []).map((e) => '$e').toList(),
      minAmount: json['min_amount'] as String? ?? '0',
      maxAmount: json['max_amount'] as String? ?? '0',
    );
  }
}

class LifiSwapCatalog {
  const LifiSwapCatalog({
    required this.assets,
    required this.sourceAssets,
    required this.destinationAssets,
    required this.swapFeeBps,
    required this.defaultSlippageBps,
  });

  final List<LifiSwapAsset> assets;
  final List<LifiSwapAsset> sourceAssets;
  final List<LifiSwapAsset> destinationAssets;
  final int swapFeeBps;
  final int defaultSlippageBps;

  factory LifiSwapCatalog.fromJson(Map<String, dynamic> json) {
    List<LifiSwapAsset> parseAssets(dynamic raw) {
      return (raw as List<dynamic>? ?? [])
          .map((e) => LifiSwapAsset.fromJson(e as Map<String, dynamic>))
          .toList();
    }

    final assets = parseAssets(json['assets']);
    final sourceAssets = parseAssets(json['source_assets']);
    final destinationAssets = parseAssets(json['destination_assets']);

    return LifiSwapCatalog(
      assets: assets,
      sourceAssets: sourceAssets.isNotEmpty ? sourceAssets : assets,
      destinationAssets: destinationAssets.isNotEmpty ? destinationAssets : assets,
      swapFeeBps: (json['swap_fee_bps'] as num?)?.toInt() ?? 0,
      defaultSlippageBps: (json['default_slippage_bps'] as num?)?.toInt() ?? 50,
    );
  }
}

class LifiSwapTransactionPayload {
  const LifiSwapTransactionPayload({
    required this.chainId,
    required this.to,
    required this.data,
    required this.value,
    this.gasLimit,
  });

  final dynamic chainId;
  final String to;
  final String data;
  final String value;
  final String? gasLimit;

  factory LifiSwapTransactionPayload.fromJson(Map<String, dynamic> json) {
    return LifiSwapTransactionPayload(
      chainId: json['chain_id'],
      to: json['to'] as String? ?? '',
      data: json['data'] as String? ?? '0x',
      value: json['value'] as String? ?? '0',
      gasLimit: json['gas_limit'] as String?,
    );
  }

  int get chainIdInt {
    if (chainId is int) return chainId as int;
    final text = '$chainId'.trim();
    if (text.startsWith('0x')) return int.parse(text.substring(2), radix: 16);
    return int.parse(text);
  }
}

class LifiSwapQuote {
  const LifiSwapQuote({
    required this.swapId,
    required this.fromAsset,
    required this.toAsset,
    required this.fromChain,
    required this.toChain,
    required this.amountIn,
    required this.vancelianFee,
    required this.networkFee,
    required this.estimatedReceive,
    required this.estimatedReceiveMin,
    required this.routeSteps,
    this.exchangeRate,
    this.networkFeeAsset,
  });

  final String swapId;
  final String fromAsset;
  final String toAsset;
  final String fromChain;
  final String toChain;
  final String amountIn;
  final String vancelianFee;
  final String networkFee;
  final String estimatedReceive;
  final String estimatedReceiveMin;
  final List<String> routeSteps;
  final String? exchangeRate;
  final String? networkFeeAsset;

  factory LifiSwapQuote.fromJson(Map<String, dynamic> json) {
    final steps = (json['route_steps'] as List<dynamic>? ?? [])
        .map((e) => (e as Map<String, dynamic>)['label'] as String? ?? '')
        .where((s) => s.isNotEmpty)
        .toList();
    return LifiSwapQuote(
      swapId: json['swap_id'] as String? ?? '',
      fromAsset: json['from_asset'] as String? ?? '',
      toAsset: json['to_asset'] as String? ?? '',
      fromChain: json['from_chain'] as String? ?? '',
      toChain: json['to_chain'] as String? ?? '',
      amountIn: json['amount_in'] as String? ?? '0',
      vancelianFee: json['vancelian_fee'] as String? ?? '0',
      networkFee: json['network_fee'] as String? ?? '0',
      estimatedReceive: json['estimated_receive'] as String? ?? '0',
      estimatedReceiveMin: json['estimated_receive_min'] as String? ?? '0',
      routeSteps: steps,
      exchangeRate: json['exchange_rate'] as String?,
      networkFeeAsset: json['network_fee_asset'] as String?,
    );
  }
}

class LifiSwapExecuteResult {
  const LifiSwapExecuteResult({
    required this.swapId,
    required this.lifecycleMessage,
    required this.transaction,
  });

  final String swapId;
  final String lifecycleMessage;
  final LifiSwapTransactionPayload? transaction;

  factory LifiSwapExecuteResult.fromJson(Map<String, dynamic> json) {
    final tx = json['transaction'];
    return LifiSwapExecuteResult(
      swapId: json['swap_id'] as String? ?? '',
      lifecycleMessage: json['lifecycle_message'] as String? ?? '',
      transaction: tx is Map<String, dynamic>
          ? LifiSwapTransactionPayload.fromJson(tx)
          : null,
    );
  }
}

class LifiSwapStatus {
  const LifiSwapStatus({
    required this.swapId,
    required this.status,
    required this.lifecycleMessage,
    this.errorMessage,
  });

  final String swapId;
  final String status;
  final String lifecycleMessage;
  final String? errorMessage;

  bool get isTerminal =>
      status == 'CONFIRMED' || status == 'FAILED' || status == 'EXPIRED';

  factory LifiSwapStatus.fromJson(Map<String, dynamic> json) {
    return LifiSwapStatus(
      swapId: json['swap_id'] as String? ?? '',
      status: json['status'] as String? ?? '',
      lifecycleMessage: json['lifecycle_message'] as String? ?? '',
      errorMessage: json['error_message'] as String?,
    );
  }
}

class LifiSwapApi {
  const LifiSwapApi();

  Future<LifiSwapCatalog> fetchCatalog() async {
    final res = await sessionBearerHttp.get(Uri.parse(Config.lifiSwapSupportedAssetsUrl));
    if (res.statusCode != 200) {
      throw LifiSwapApiException(_extractError(res));
    }
    return LifiSwapCatalog.fromJson(jsonDecode(res.body) as Map<String, dynamic>);
  }

  Future<LifiSwapQuote> requestQuote({
    required String fromAsset,
    required String toAsset,
    required String amount,
    required String fromChain,
    required String toChain,
  }) async {
    final res = await sessionBearerHttp.post(
      Uri.parse(Config.lifiSwapQuoteUrl),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({
        'from_asset': fromAsset,
        'to_asset': toAsset,
        'amount': amount,
        'from_chain': fromChain,
        'to_chain': toChain,
      }),
    );
    if (res.statusCode != 200) {
      throw LifiSwapApiException(_extractError(res));
    }
    return LifiSwapQuote.fromJson(jsonDecode(res.body) as Map<String, dynamic>);
  }

  Future<LifiSwapExecuteResult> prepareExecute(String swapId) async {
    final res = await sessionBearerHttp.post(
      Uri.parse(Config.lifiSwapExecuteUrl),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'swap_id': swapId}),
    );
    if (res.statusCode != 200) {
      throw LifiSwapApiException(_extractError(res));
    }
    return LifiSwapExecuteResult.fromJson(jsonDecode(res.body) as Map<String, dynamic>);
  }

  Future<LifiSwapStatus> submitTx(String swapId, String txHash) async {
    final res = await sessionBearerHttp.post(
      Uri.parse(Config.lifiSwapStatusUrl(swapId)),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'tx_hash': txHash}),
    );
    if (res.statusCode != 200) {
      throw LifiSwapApiException(_extractError(res));
    }
    return LifiSwapStatus.fromJson(jsonDecode(res.body) as Map<String, dynamic>);
  }

  Future<LifiSwapStatus> fetchStatus(String swapId) async {
    final res = await sessionBearerHttp.get(Uri.parse(Config.lifiSwapStatusUrl(swapId)));
    if (res.statusCode != 200) {
      throw LifiSwapApiException(_extractError(res));
    }
    return LifiSwapStatus.fromJson(jsonDecode(res.body) as Map<String, dynamic>);
  }

  Future<LifiSwapStatus> pollUntilTerminal(
    String swapId, {
    Duration timeout = const Duration(minutes: 5),
    Duration interval = const Duration(seconds: 5),
  }) async {
    final started = DateTime.now();
    while (DateTime.now().difference(started) < timeout) {
      final status = await fetchStatus(swapId);
      if (status.isTerminal) return status;
      await Future<void>.delayed(interval);
    }
    return fetchStatus(swapId);
  }

  String _extractError(http.Response res) {
    try {
      final body = jsonDecode(res.body) as Map<String, dynamic>;
      final detail = body['detail'];
      if (detail is Map<String, dynamic>) {
        return detail['message'] as String? ?? 'Swap error';
      }
      return body['message'] as String? ?? 'Swap error (${res.statusCode})';
    } catch (_) {
      return 'Swap error (${res.statusCode})';
    }
  }
}

class LifiSwapApiException implements Exception {
  LifiSwapApiException(this.message);
  final String message;

  @override
  String toString() => message;
}
