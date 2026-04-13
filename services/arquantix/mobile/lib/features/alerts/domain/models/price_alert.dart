enum PriceSource {
  mid,
  bid,
  ask;

  static PriceSource fromString(String? v) =>
      PriceSource.values.firstWhere((e) => e.name == v, orElse: () => PriceSource.mid);
}

class PriceAlert {
  final String id;
  final String asset;
  final double targetPrice;
  final String direction;
  final PriceSource priceSource;
  final String status;
  final String actionType;
  final String triggerMode;
  final int triggerCount;
  final int cooldownSeconds;
  final String? executionStatus;
  final DateTime createdAt;
  final DateTime? triggeredAt;
  final double? triggeredPrice;

  const PriceAlert({
    required this.id,
    required this.asset,
    required this.targetPrice,
    required this.direction,
    this.priceSource = PriceSource.mid,
    required this.status,
    required this.actionType,
    this.triggerMode = 'once',
    this.triggerCount = 0,
    this.cooldownSeconds = 0,
    this.executionStatus,
    required this.createdAt,
    this.triggeredAt,
    this.triggeredPrice,
  });

  factory PriceAlert.fromJson(Map<String, dynamic> json) {
    return PriceAlert(
      id: json['id'] as String,
      asset: json['asset'] as String,
      targetPrice: (json['target_price'] as num).toDouble(),
      direction: json['direction'] as String,
      priceSource: PriceSource.fromString(json['price_source'] as String?),
      status: json['status'] as String,
      actionType: json['action_type'] as String? ?? 'alert',
      triggerMode: json['trigger_mode'] as String? ?? 'once',
      triggerCount: json['trigger_count'] as int? ?? 0,
      cooldownSeconds: json['cooldown_seconds'] as int? ?? 0,
      executionStatus: json['execution_status'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
      triggeredAt: json['triggered_at'] != null
          ? DateTime.parse(json['triggered_at'] as String)
          : null,
      triggeredPrice: json['triggered_price'] != null
          ? (json['triggered_price'] as num).toDouble()
          : null,
    );
  }

  bool get isActive => status == 'active';
  bool get isTriggered => status == 'triggered';
  bool get isUp => direction == 'up';
  bool get isRecurring => triggerMode == 'recurring';

  /// Distance en pourcentage entre le prix actuel et le prix cible.
  /// Positif = au-dessus du prix actuel, négatif = en-dessous.
  double? distancePercent(double? currentPrice) {
    if (currentPrice == null || currentPrice == 0) return null;
    return ((targetPrice - currentPrice) / currentPrice) * 100;
  }
}
