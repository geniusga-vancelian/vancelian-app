class PortfolioAssetAllocation {
  const PortfolioAssetAllocation({
    required this.asset,
    required this.currentValue,
    required this.pnl,
    required this.weight,
  });

  final String asset;
  final double currentValue;
  final double pnl;
  final double weight;

  factory PortfolioAssetAllocation.fromJson(Map<String, dynamic> json) {
    return PortfolioAssetAllocation(
      asset: json['asset'] as String? ?? '',
      currentValue: _d(json['current_value']),
      pnl: _d(json['pnl']),
      weight: _d(json['weight']),
    );
  }

  static double _d(dynamic v) {
    if (v == null) return 0;
    if (v is num) return v.toDouble();
    return double.tryParse(v.toString()) ?? 0;
  }
}

class PortfolioContribution {
  const PortfolioContribution({
    required this.asset,
    required this.pnl,
    required this.contributionPct,
  });

  final String asset;
  final double pnl;
  final double contributionPct;

  factory PortfolioContribution.fromJson(Map<String, dynamic> json) {
    return PortfolioContribution(
      asset: json['asset'] as String? ?? '',
      pnl: _d(json['pnl']),
      contributionPct: _d(json['contribution_pct']),
    );
  }

  static double _d(dynamic v) {
    if (v == null) return 0;
    if (v is num) return v.toDouble();
    return double.tryParse(v.toString()) ?? 0;
  }
}

class SourceBreakdown {
  const SourceBreakdown({
    required this.directValue,
    required this.directPct,
    required this.bundleValue,
    required this.bundlePct,
    required this.bundleCashValue,
    required this.bundleCashPct,
  });

  final double directValue;
  final double directPct;
  final double bundleValue;
  final double bundlePct;
  final double bundleCashValue;
  final double bundleCashPct;

  factory SourceBreakdown.fromJson(Map<String, dynamic> json) {
    return SourceBreakdown(
      directValue: _d(json['direct_value']),
      directPct: _d(json['direct_pct']),
      bundleValue: _d(json['bundle_value']),
      bundlePct: _d(json['bundle_pct']),
      bundleCashValue: _d(json['bundle_cash_value']),
      bundleCashPct: _d(json['bundle_cash_pct']),
    );
  }

  static double _d(dynamic v) {
    if (v == null) return 0;
    if (v is num) return v.toDouble();
    return double.tryParse(v.toString()) ?? 0;
  }
}

class DeploymentInfo {
  const DeploymentInfo({
    required this.investedPct,
    required this.cashPct,
    required this.cashValue,
    required this.directWallets,
    required this.activeBundles,
  });

  final double investedPct;
  final double cashPct;
  final double cashValue;
  final int directWallets;
  final int activeBundles;

  factory DeploymentInfo.fromJson(Map<String, dynamic> json) {
    return DeploymentInfo(
      investedPct: _d(json['invested_pct']),
      cashPct: _d(json['cash_pct']),
      cashValue: _d(json['cash_value']),
      directWallets: json['direct_wallets'] as int? ?? 0,
      activeBundles: json['active_bundles'] as int? ?? 0,
    );
  }

  static double _d(dynamic v) {
    if (v == null) return 0;
    if (v is num) return v.toDouble();
    return double.tryParse(v.toString()) ?? 0;
  }
}

class ActivityInfo {
  const ActivityInfo({
    required this.directTrades,
    required this.bundleInvestEvents,
    required this.rebalanceEvents,
    this.lastActivity,
  });

  final int directTrades;
  final int bundleInvestEvents;
  final int rebalanceEvents;
  final DateTime? lastActivity;

  factory ActivityInfo.fromJson(Map<String, dynamic> json) {
    return ActivityInfo(
      directTrades: json['direct_trades'] as int? ?? 0,
      bundleInvestEvents: json['bundle_invest_events'] as int? ?? 0,
      rebalanceEvents: json['rebalance_events'] as int? ?? 0,
      lastActivity: json['last_activity'] != null
          ? DateTime.tryParse(json['last_activity'].toString())
          : null,
    );
  }
}

class RiskInfo {
  const RiskInfo({
    required this.assetsCount,
    this.concentrationAsset,
    required this.concentrationPct,
    this.volatility30d,
    this.maxDrawdown,
  });

  final int assetsCount;
  final String? concentrationAsset;
  final double concentrationPct;
  final double? volatility30d;
  final double? maxDrawdown;

  factory RiskInfo.fromJson(Map<String, dynamic> json) {
    return RiskInfo(
      assetsCount: json['assets_count'] as int? ?? 0,
      concentrationAsset: json['concentration_asset'] as String?,
      concentrationPct: _d(json['concentration_pct']),
      volatility30d: _dn(json['volatility_30d']),
      maxDrawdown: _dn(json['max_drawdown']),
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
}

class PortfolioStatistics {
  const PortfolioStatistics({
    required this.currency,
    required this.currentValue,
    required this.totalInvested,
    required this.totalPnl,
    required this.performancePct,
    required this.realizedPnl,
    required this.unrealizedPnl,
    required this.allocation,
    required this.contributions,
    required this.sourceBreakdown,
    required this.deployment,
    required this.activity,
    required this.risk,
  });

  final String currency;
  final double currentValue;
  final double totalInvested;
  final double totalPnl;
  final double performancePct;
  final double realizedPnl;
  final double unrealizedPnl;
  final List<PortfolioAssetAllocation> allocation;
  final List<PortfolioContribution> contributions;
  final SourceBreakdown sourceBreakdown;
  final DeploymentInfo deployment;
  final ActivityInfo activity;
  final RiskInfo risk;

  factory PortfolioStatistics.fromJson(Map<String, dynamic> json) {
    final perf = json['performance'] as Map<String, dynamic>? ?? {};
    final rawAlloc = json['allocation'] as List<dynamic>? ?? [];
    final rawContrib = json['contributions'] as List<dynamic>? ?? [];

    return PortfolioStatistics(
      currency: json['currency'] as String? ?? 'EUR',
      currentValue: _d(perf['current_value']),
      totalInvested: _d(perf['total_invested']),
      totalPnl: _d(perf['total_pnl']),
      performancePct: _d(perf['performance_pct']),
      realizedPnl: _d(perf['realized_pnl']),
      unrealizedPnl: _d(perf['unrealized_pnl']),
      allocation: rawAlloc
          .whereType<Map<String, dynamic>>()
          .map(PortfolioAssetAllocation.fromJson)
          .toList(growable: false),
      contributions: rawContrib
          .whereType<Map<String, dynamic>>()
          .map(PortfolioContribution.fromJson)
          .toList(growable: false),
      sourceBreakdown: SourceBreakdown.fromJson(
        json['source_breakdown'] as Map<String, dynamic>? ?? {},
      ),
      deployment: DeploymentInfo.fromJson(
        json['deployment'] as Map<String, dynamic>? ?? {},
      ),
      activity: ActivityInfo.fromJson(
        json['activity'] as Map<String, dynamic>? ?? {},
      ),
      risk: RiskInfo.fromJson(
        json['risk'] as Map<String, dynamic>? ?? {},
      ),
    );
  }

  static double _d(dynamic v) {
    if (v == null) return 0;
    if (v is num) return v.toDouble();
    return double.tryParse(v.toString()) ?? 0;
  }
}
