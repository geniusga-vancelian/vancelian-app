/// Model for the transaction detail endpoint response.

class TransactionDetail {
  final String id;
  final String transactionType;
  final String? transactionKind;
  final String direction;
  final double amount;
  final String currency;
  final String currencySymbol;
  final String status;
  final String createdAt;
  final String? updatedAt;

  final String title;
  final String statusLabel;

  final String? externalReference;
  final String? providerReference;
  final String? providerName;

  final String? remitterName;
  final String? remitterIban;
  final String? remitterBankName;

  final String? accountHolderName;
  final String? targetIban;

  final String? bookingDate;
  final String? valueDate;

  final String? narrative;

  const TransactionDetail({
    required this.id,
    required this.transactionType,
    this.transactionKind,
    required this.direction,
    required this.amount,
    required this.currency,
    required this.currencySymbol,
    required this.status,
    required this.createdAt,
    this.updatedAt,
    required this.title,
    required this.statusLabel,
    this.externalReference,
    this.providerReference,
    this.providerName,
    this.remitterName,
    this.remitterIban,
    this.remitterBankName,
    this.accountHolderName,
    this.targetIban,
    this.bookingDate,
    this.valueDate,
    this.narrative,
  });

  bool get isCredit => direction == 'credit';

  factory TransactionDetail.fromJson(Map<String, dynamic> json) {
    return TransactionDetail(
      id: json['id'] as String,
      transactionType: json['transaction_type'] as String,
      transactionKind: json['transaction_kind'] as String?,
      direction: json['direction'] as String,
      amount: double.tryParse(json['amount'].toString()) ?? 0,
      currency: json['currency'] as String? ?? 'EUR',
      currencySymbol: json['currency_symbol'] as String? ?? '€',
      status: json['status'] as String,
      createdAt: json['created_at'] as String,
      updatedAt: json['updated_at'] as String?,
      title: json['title'] as String? ?? 'Transaction',
      statusLabel: json['status_label'] as String? ?? json['status'] as String,
      externalReference: json['external_reference'] as String?,
      providerReference: json['provider_reference'] as String?,
      providerName: json['provider_name'] as String?,
      remitterName: json['remitter_name'] as String?,
      remitterIban: json['remitter_iban'] as String?,
      remitterBankName: json['remitter_bank_name'] as String?,
      accountHolderName: json['account_holder_name'] as String?,
      targetIban: json['target_iban'] as String?,
      bookingDate: json['booking_date'] as String?,
      valueDate: json['value_date'] as String?,
      narrative: json['narrative'] as String?,
    );
  }
}
