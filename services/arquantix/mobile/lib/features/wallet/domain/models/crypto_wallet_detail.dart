class CryptoWalletDetail {
  const CryptoWalletDetail({
    required this.asset,
    required this.name,
    required this.iconKey,
    required this.volume,
    this.currentPriceEur,
    this.currentPriceUsd,
    required this.totalValueEur,
    this.totalValueUsd,
    this.avgBuyPriceEur,
    this.avgBuyPriceUsd,
    this.averagePurchasePrice,
    this.costBasis,
    this.unrealizedGainEur,
    this.unrealizedGainUsd,
    this.unrealizedGains,
    this.unrealizedGainsPct,
    required this.realizedGainEur,
    this.realizedGainUsd,
    required this.realizedGains,
    this.totalGainEur,
    this.totalGainUsd,
    this.totalGains,
    this.totalGainsPct,
  });

  final String asset;
  final String name;
  final String iconKey;
  final String volume;
  final double? currentPriceEur;
  final double? currentPriceUsd;
  final double totalValueEur;
  final double? totalValueUsd;
  final double? avgBuyPriceEur;
  final double? avgBuyPriceUsd;
  final double? averagePurchasePrice;
  final double? costBasis;
  final double? unrealizedGainEur;
  final double? unrealizedGainUsd;
  final double? unrealizedGains;
  final double? unrealizedGainsPct;
  final double realizedGainEur;
  final double? realizedGainUsd;
  final double realizedGains;
  final double? totalGainEur;
  final double? totalGainUsd;
  final double? totalGains;
  final double? totalGainsPct;

  factory CryptoWalletDetail.fromJson(Map<String, dynamic> json) {
    return CryptoWalletDetail(
      asset: json['asset'] as String? ?? '',
      name: json['name'] as String? ?? '',
      iconKey: json['icon_key'] as String? ?? '',
      volume: json['volume'] as String? ?? '0',
      currentPriceEur: _parseDouble(json['current_price_eur']),
      currentPriceUsd: _parseDouble(json['current_price_usd']),
      totalValueEur: _parseDouble(json['total_value_eur']) ?? 0,
      totalValueUsd: _parseDouble(json['total_value_usd']),
      avgBuyPriceEur: _parseDouble(json['avg_buy_price_eur']),
      avgBuyPriceUsd: _parseDouble(json['avg_buy_price_usd']),
      averagePurchasePrice: _parseDouble(json['average_purchase_price']),
      costBasis: _parseDouble(json['cost_basis']),
      unrealizedGainEur: _parseDouble(json['unrealized_gain_eur']),
      unrealizedGainUsd: _parseDouble(json['unrealized_gain_usd']),
      unrealizedGains: _parseDouble(json['unrealized_gains']),
      unrealizedGainsPct: _parseDouble(json['unrealized_gains_pct']),
      realizedGainEur: _parseDouble(json['realized_gain_eur']) ?? 0,
      realizedGainUsd: _parseDouble(json['realized_gain_usd']),
      realizedGains: _parseDouble(json['realized_gains']) ?? 0,
      totalGainEur: _parseDouble(json['total_gain_eur']),
      totalGainUsd: _parseDouble(json['total_gain_usd']),
      totalGains: _parseDouble(json['total_gains']),
      totalGainsPct: _parseDouble(json['total_gains_pct']),
    );
  }

  static double? _parseDouble(dynamic v) {
    if (v == null) return null;
    return double.tryParse(v.toString().replaceAll('+', ''));
  }
}
