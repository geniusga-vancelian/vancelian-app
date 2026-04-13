/// Données agrégées des positions placements (lending earn).
class PlacementsData {
  const PlacementsData({
    required this.totalValueEur,
    required this.totalAccruedInterestEur,
    required this.positionsCount,
    required this.positions,
  });

  final double totalValueEur;
  final double totalAccruedInterestEur;
  final int positionsCount;
  final List<EarnPositionItem> positions;

  factory PlacementsData.fromJson(Map<String, dynamic> json) {
    final positions = (json['positions'] as List<dynamic>? ?? [])
        .map((e) => EarnPositionItem.fromJson(e as Map<String, dynamic>))
        .toList();
    return PlacementsData(
      totalValueEur:
          double.tryParse(json['total_earn_value_eur']?.toString() ?? '0') ?? 0,
      totalAccruedInterestEur: double.tryParse(
              json['total_accrued_interest_eur']?.toString() ?? '0') ??
          0,
      positionsCount: (json['positions_count'] as int?) ?? 0,
      positions: positions,
    );
  }
}

/// Position earn par asset (agrégée depuis lending atoms + supply commitments).
class EarnPositionItem {
  const EarnPositionItem({
    required this.asset,
    this.poolId,
    this.lendingPoolProductId,
    this.projectId,
    required this.totalSupplied,
    required this.earningAmount,
    required this.idleAmount,
    required this.accruedInterest,
    required this.totalValue,
    required this.valueEur,
    required this.apy,
    required this.poolUtilization,
  });

  final String asset;
  final String? poolId;
  final String? lendingPoolProductId;
  final String? projectId;
  final double totalSupplied;
  final double earningAmount;
  final double idleAmount;
  final double accruedInterest;
  final double totalValue;
  final double valueEur;
  final double apy;
  final double poolUtilization;

  factory EarnPositionItem.fromJson(Map<String, dynamic> json) {
    return EarnPositionItem(
      asset: json['asset'] as String? ?? '',
      poolId: json['pool_id'] as String?,
      lendingPoolProductId: json['lending_pool_product_id'] as String?,
      projectId: json['project_id'] as String?,
      totalSupplied:
          double.tryParse(json['total_supplied']?.toString() ?? '0') ?? 0,
      earningAmount:
          double.tryParse(json['earning_amount']?.toString() ?? '0') ?? 0,
      idleAmount:
          double.tryParse(json['idle_amount']?.toString() ?? '0') ?? 0,
      accruedInterest:
          double.tryParse(json['accrued_interest']?.toString() ?? '0') ?? 0,
      totalValue:
          double.tryParse(json['total_value']?.toString() ?? '0') ?? 0,
      valueEur: double.tryParse(json['value_eur']?.toString() ?? '0') ?? 0,
      apy: double.tryParse(json['apy']?.toString() ?? '0') ?? 0,
      poolUtilization:
          double.tryParse(json['pool_utilization']?.toString() ?? '0') ?? 0,
    );
  }
}

/// Position placement enrichie : earn position + métadonnées projet CMS.
class PlacementPosition {
  const PlacementPosition({
    required this.projectId,
    this.poolId,
    this.lendingPoolProductId,
    required this.projectTitle,
    required this.projectCategory,
    this.projectImageUrl,
    required this.lendingAsset,
    required this.totalSupplied,
    required this.accruedInterest,
    required this.totalValue,
    required this.valueEur,
    required this.apy,
    required this.status,
    this.durationMonths,
    this.raised,
    this.target,
    this.investorsCount,
    this.progress,
  });

  final String projectId;
  final String? poolId;
  final String? lendingPoolProductId;
  final String projectTitle;
  final String projectCategory;
  final String? projectImageUrl;
  final String lendingAsset;
  final double totalSupplied;
  final double accruedInterest;
  final double totalValue;
  final double valueEur;
  final double apy;
  final String status;
  final int? durationMonths;
  final double? raised;
  final double? target;
  final int? investorsCount;
  final double? progress;

  String get statusLabel {
    switch (status) {
      case 'fundraising':
        return 'En levée';
      case 'active':
        return 'Actif';
      case 'repaid':
        return 'Terminé';
      default:
        return status;
    }
  }
}
