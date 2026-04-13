class CryptoPositionsData {
  const CryptoPositionsData({
    required this.totalValueEur,
    this.totalValueUsd,
    required this.positionsCount,
    required this.positions,
  });

  final double totalValueEur;
  final double? totalValueUsd;
  final int positionsCount;
  final List<CryptoPositionItem> positions;

  factory CryptoPositionsData.fromJson(Map<String, dynamic> json) {
    final summary = json['summary'] as Map<String, dynamic>? ?? {};
    final list = json['positions'] as List<dynamic>? ?? [];

    return CryptoPositionsData(
      totalValueEur: double.tryParse(summary['total_value_eur']?.toString() ?? '0') ?? 0,
      totalValueUsd: double.tryParse(summary['total_value_usd']?.toString() ?? ''),
      positionsCount: (summary['positions_count'] as int?) ?? 0,
      positions: list
          .map((e) => CryptoPositionItem.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }
}

class CryptoPositionItem {
  const CryptoPositionItem({
    required this.asset,
    required this.name,
    required this.balance,
    required this.availableBalance,
    this.priceEur,
    this.estimatedValueEur,
    this.priceUsd,
    this.estimatedValueUsd,
    this.performance1dPct,
    required this.iconKey,
  });

  final String asset;
  final String name;
  final double balance;
  final double availableBalance;
  final double? priceEur;
  final double? estimatedValueEur;
  final double? priceUsd;
  final double? estimatedValueUsd;
  final double? performance1dPct;
  final String iconKey;

  factory CryptoPositionItem.fromJson(Map<String, dynamic> json) {
    return CryptoPositionItem(
      asset: json['asset'] as String? ?? '',
      name: json['name'] as String? ?? '',
      balance: double.tryParse(json['balance']?.toString() ?? '0') ?? 0,
      availableBalance: double.tryParse(json['available_balance']?.toString() ?? '0') ?? 0,
      priceEur: json['price_eur'] != null
          ? double.tryParse(json['price_eur'].toString())
          : null,
      estimatedValueEur: json['estimated_value_eur'] != null
          ? double.tryParse(json['estimated_value_eur'].toString())
          : null,
      priceUsd: json['price_usd'] != null
          ? double.tryParse(json['price_usd'].toString())
          : null,
      estimatedValueUsd: json['estimated_value_usd'] != null
          ? double.tryParse(json['estimated_value_usd'].toString())
          : null,
      performance1dPct: json['performance_1d_pct'] != null
          ? double.tryParse(json['performance_1d_pct'].toString().replaceAll('+', ''))
          : null,
      iconKey: json['icon_key'] as String? ?? '',
    );
  }
}
