class GlobalAllocationItem {
  const GlobalAllocationItem({
    required this.asset,
    required this.value,
    required this.pnl,
    required this.weight,
  });

  final String asset;
  final double value;
  final double pnl;
  final double weight;

  factory GlobalAllocationItem.fromJson(Map<String, dynamic> json) {
    return GlobalAllocationItem(
      asset: json['asset'] as String? ?? '',
      value: _d(json['value']),
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

class GlobalContribution {
  const GlobalContribution({
    required this.asset,
    required this.pnl,
    required this.contributionPct,
  });

  final String asset;
  final double pnl;
  final double contributionPct;

  factory GlobalContribution.fromJson(Map<String, dynamic> json) {
    return GlobalContribution(
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

class GlobalAccountContribution {
  const GlobalAccountContribution({
    required this.account,
    required this.value,
    required this.pnl,
    required this.contributionPct,
  });

  final String account;
  final double value;
  final double pnl;
  final double contributionPct;

  factory GlobalAccountContribution.fromJson(Map<String, dynamic> json) {
    return GlobalAccountContribution(
      account: json['account'] as String? ?? '',
      value: _d(json['value']),
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

class GlobalBreakdown {
  const GlobalBreakdown({
    required this.fiat,
    required this.fiatPct,
    required this.cryptoDirect,
    required this.cryptoDirectPct,
    required this.bundles,
    required this.bundlesPct,
  });

  final double fiat;
  final double fiatPct;
  final double cryptoDirect;
  final double cryptoDirectPct;
  final double bundles;
  final double bundlesPct;

  factory GlobalBreakdown.fromJson(Map<String, dynamic> json) {
    return GlobalBreakdown(
      fiat: _d(json['fiat']),
      fiatPct: _d(json['fiat_pct']),
      cryptoDirect: _d(json['crypto_direct']),
      cryptoDirectPct: _d(json['crypto_direct_pct']),
      bundles: _d(json['bundles']),
      bundlesPct: _d(json['bundles_pct']),
    );
  }

  static double _d(dynamic v) {
    if (v == null) return 0;
    if (v is num) return v.toDouble();
    return double.tryParse(v.toString()) ?? 0;
  }
}

class GlobalCashflow {
  const GlobalCashflow({
    required this.deposits,
    required this.withdrawals,
    required this.netFlow,
  });

  final double deposits;
  final double withdrawals;
  final double netFlow;

  factory GlobalCashflow.fromJson(Map<String, dynamic> json) {
    return GlobalCashflow(
      deposits: _d(json['deposits']),
      withdrawals: _d(json['withdrawals']),
      netFlow: _d(json['net_flow']),
    );
  }

  static double _d(dynamic v) {
    if (v == null) return 0;
    if (v is num) return v.toDouble();
    return double.tryParse(v.toString()) ?? 0;
  }
}

class GlobalActivity {
  const GlobalActivity({
    required this.directTrades,
    required this.bundleInvestEvents,
    required this.rebalanceEvents,
    required this.depositCount,
    required this.withdrawalCount,
    this.lastActivity,
  });

  final int directTrades;
  final int bundleInvestEvents;
  final int rebalanceEvents;
  final int depositCount;
  final int withdrawalCount;
  final DateTime? lastActivity;

  factory GlobalActivity.fromJson(Map<String, dynamic> json) {
    return GlobalActivity(
      directTrades: json['direct_trades'] as int? ?? 0,
      bundleInvestEvents: json['bundle_invest_events'] as int? ?? 0,
      rebalanceEvents: json['rebalance_events'] as int? ?? 0,
      depositCount: json['deposit_count'] as int? ?? 0,
      withdrawalCount: json['withdrawal_count'] as int? ?? 0,
      lastActivity: json['last_activity'] != null
          ? DateTime.tryParse(json['last_activity'].toString())
          : null,
    );
  }
}

class GlobalRisk {
  const GlobalRisk({
    required this.assetsCount,
    this.concentrationAsset,
    required this.concentrationPct,
    this.hhi,
  });

  final int assetsCount;
  final String? concentrationAsset;
  final double concentrationPct;
  final double? hhi;

  factory GlobalRisk.fromJson(Map<String, dynamic> json) {
    return GlobalRisk(
      assetsCount: json['assets_count'] as int? ?? 0,
      concentrationAsset: json['concentration_asset'] as String?,
      concentrationPct: _d(json['concentration_pct']),
      hhi: _dn(json['hhi']),
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

class GlobalStatistics {
  const GlobalStatistics({
    required this.currency,
    required this.currentValue,
    required this.totalInvested,
    required this.totalPnl,
    required this.performancePct,
    required this.realizedPnl,
    required this.unrealizedPnl,
    required this.allocation,
    required this.contributions,
    required this.accountContributions,
    required this.breakdown,
    required this.cashflow,
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
  final List<GlobalAllocationItem> allocation;
  final List<GlobalContribution> contributions;
  final List<GlobalAccountContribution> accountContributions;
  final GlobalBreakdown breakdown;
  final GlobalCashflow cashflow;
  final GlobalActivity activity;
  final GlobalRisk risk;

  factory GlobalStatistics.fromJson(Map<String, dynamic> json) {
    final perf = json['performance'] as Map<String, dynamic>? ?? {};
    final rawAlloc = json['allocation'] as List<dynamic>? ?? [];
    final rawContrib = json['contributions'] as List<dynamic>? ?? [];
    final rawAccContrib = json['account_contributions'] as List<dynamic>? ?? [];

    return GlobalStatistics(
      currency: json['currency'] as String? ?? 'EUR',
      currentValue: _d(perf['current_value']),
      totalInvested: _d(perf['total_invested']),
      totalPnl: _d(perf['total_pnl']),
      performancePct: _d(perf['performance_pct']),
      realizedPnl: _d(perf['realized_pnl']),
      unrealizedPnl: _d(perf['unrealized_pnl']),
      allocation: rawAlloc
          .whereType<Map<String, dynamic>>()
          .map(GlobalAllocationItem.fromJson)
          .toList(growable: false),
      contributions: rawContrib
          .whereType<Map<String, dynamic>>()
          .map(GlobalContribution.fromJson)
          .toList(growable: false),
      accountContributions: rawAccContrib
          .whereType<Map<String, dynamic>>()
          .map(GlobalAccountContribution.fromJson)
          .toList(growable: false),
      breakdown: GlobalBreakdown.fromJson(
        json['breakdown'] as Map<String, dynamic>? ?? {},
      ),
      cashflow: GlobalCashflow.fromJson(
        json['cashflow'] as Map<String, dynamic>? ?? {},
      ),
      activity: GlobalActivity.fromJson(
        json['activity'] as Map<String, dynamic>? ?? {},
      ),
      risk: GlobalRisk.fromJson(
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

class GlobalHistoryResult {
  const GlobalHistoryResult({required this.points, this.maxDrawdown});

  final List<GlobalHistoryPoint> points;
  final double? maxDrawdown;
}

class GlobalHistoryPoint {
  const GlobalHistoryPoint({
    required this.timestamp,
    required this.totalValue,
    required this.performanceValue,
  });

  final DateTime timestamp;
  final double totalValue;
  final double performanceValue;

  factory GlobalHistoryPoint.fromJson(Map<String, dynamic> json) {
    return GlobalHistoryPoint(
      timestamp: DateTime.parse(json['timestamp'] as String),
      totalValue: (json['total_value'] as num?)?.toDouble() ?? 0,
      performanceValue: (json['performance_value'] as num?)?.toDouble() ?? 0,
    );
  }
}
