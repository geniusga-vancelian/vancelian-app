class TriggerOrder {
  final String id;
  final String asset;
  final String side;
  final String orderType;
  final double triggerPrice;
  final double amount;
  final int? slippageBps;
  final String direction;
  final String priceSource;
  final String status;
  final String? executionStatus;
  final double? executionPrice;
  final double? filledAmount;
  final double? remainingAmount;
  final String? orderId;
  final String? failureReason;
  final bool canRetryRemaining;
  final DateTime createdAt;
  final DateTime? triggeredAt;
  final double? triggeredPrice;

  const TriggerOrder({
    required this.id,
    required this.asset,
    required this.side,
    required this.orderType,
    required this.triggerPrice,
    required this.amount,
    this.slippageBps,
    required this.direction,
    required this.priceSource,
    required this.status,
    this.executionStatus,
    this.executionPrice,
    this.filledAmount,
    this.remainingAmount,
    this.orderId,
    this.failureReason,
    this.canRetryRemaining = false,
    required this.createdAt,
    this.triggeredAt,
    this.triggeredPrice,
  });

  factory TriggerOrder.fromJson(Map<String, dynamic> json) {
    return TriggerOrder(
      id: json['id'] as String,
      asset: json['asset'] as String,
      side: json['side'] as String? ?? 'buy',
      orderType: json['order_type'] as String? ?? 'limit',
      triggerPrice: (json['trigger_price'] as num).toDouble(),
      amount: (json['amount'] as num?)?.toDouble() ?? 0,
      slippageBps: json['slippage_bps'] as int?,
      direction: json['direction'] as String? ?? 'down',
      priceSource: json['price_source'] as String? ?? 'ask',
      status: json['status'] as String,
      executionStatus: json['execution_status'] as String?,
      executionPrice: json['execution_price'] != null
          ? (json['execution_price'] as num).toDouble()
          : null,
      filledAmount: json['filled_amount'] != null
          ? (json['filled_amount'] as num).toDouble()
          : null,
      remainingAmount: json['remaining_amount'] != null
          ? (json['remaining_amount'] as num).toDouble()
          : null,
      orderId: json['order_id'] as String?,
      failureReason: json['failure_reason'] as String?,
      canRetryRemaining: json['can_retry_remaining'] as bool? ?? false,
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
  bool get isExecuted => executionStatus == 'executed';
  bool get isPartial => executionStatus == 'partial';
  bool get isFailed => executionStatus == 'failed';
  bool get isPending =>
      (isTriggered && (executionStatus == 'pending' || executionStatus == null));
  bool get isBuy => side == 'buy';

  String get typeLabel {
    final s = side.toUpperCase();
    final t = orderType.toUpperCase();
    return '$s $t';
  }

  double? distancePercent(double? currentPrice) {
    if (currentPrice == null || currentPrice == 0) return null;
    return ((triggerPrice - currentPrice) / currentPrice) * 100;
  }
}
