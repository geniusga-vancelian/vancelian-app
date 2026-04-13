class WalletStatistics {
  const WalletStatistics({
    required this.asset,
    required this.currency,
    required this.currentValue,
    required this.positionSize,
    required this.averageEntryPrice,
    required this.currentPrice,
    required this.unrealizedPnl,
    required this.realizedPnl,
    required this.totalPnl,
    this.firstTradeAt,
    this.lastTradeAt,
    required this.tradeCount,
    required this.buyCount,
    required this.sellCount,
    required this.totalBought,
    required this.totalSold,
    required this.avgBuyPrice,
    this.avgSellPrice,
    required this.positionAgeDays,
    this.breakEvenDistancePct,
    this.volatility30d,
    this.maxDrawdown,
    this.portfolioWeight,
  });

  final String asset;
  final String currency;
  final double currentValue;
  final double positionSize;
  final double averageEntryPrice;
  final double currentPrice;
  final double unrealizedPnl;
  final double realizedPnl;
  final double totalPnl;
  final DateTime? firstTradeAt;
  final DateTime? lastTradeAt;
  final int tradeCount;
  final int buyCount;
  final int sellCount;
  final double totalBought;
  final double totalSold;
  final double avgBuyPrice;
  final double? avgSellPrice;
  final int positionAgeDays;
  final double? breakEvenDistancePct;
  final double? volatility30d;
  final double? maxDrawdown;
  final double? portfolioWeight;

  factory WalletStatistics.fromJson(Map<String, dynamic> json) {
    return WalletStatistics(
      asset: json['asset'] as String? ?? '',
      currency: json['currency'] as String? ?? 'EUR',
      currentValue: _d(json['current_value']),
      positionSize: _d(json['position_size']),
      averageEntryPrice: _d(json['average_entry_price']),
      currentPrice: _d(json['current_price']),
      unrealizedPnl: _d(json['unrealized_pnl']),
      realizedPnl: _d(json['realized_pnl']),
      totalPnl: _d(json['total_pnl']),
      firstTradeAt: _dt(json['first_trade_at']),
      lastTradeAt: _dt(json['last_trade_at']),
      tradeCount: json['trade_count'] as int? ?? 0,
      buyCount: json['buy_count'] as int? ?? 0,
      sellCount: json['sell_count'] as int? ?? 0,
      totalBought: _d(json['total_bought']),
      totalSold: _d(json['total_sold']),
      avgBuyPrice: _d(json['avg_buy_price']),
      avgSellPrice: json['avg_sell_price'] != null ? _d(json['avg_sell_price']) : null,
      positionAgeDays: json['position_age_days'] as int? ?? 0,
      breakEvenDistancePct: _dn(json['break_even_distance_pct']),
      volatility30d: _dn(json['volatility_30d']),
      maxDrawdown: _dn(json['max_drawdown']),
      portfolioWeight: _dn(json['portfolio_weight']),
    );
  }

  static double _d(dynamic v) {
    if (v == null) return 0;
    if (v is num) return v.toDouble();
    return double.tryParse(v.toString()) ?? 0;
  }

  static double? _dn(dynamic v) {
    if (v == null) return null;
    if (v is num) return v.toDouble();
    return double.tryParse(v.toString());
  }

  static DateTime? _dt(dynamic v) {
    if (v == null) return null;
    if (v is String) return DateTime.tryParse(v);
    return null;
  }
}
