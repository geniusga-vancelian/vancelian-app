/// Models for the Cash balance endpoint (/api/mobile/flutter/cash).

class CashClient {
  final String id;
  final String email;
  final String status;
  final String kycStatus;

  const CashClient({
    required this.id,
    required this.email,
    required this.status,
    required this.kycStatus,
  });

  factory CashClient.fromJson(Map<String, dynamic> json) {
    return CashClient(
      id: json['id'] as String,
      email: json['email'] as String,
      status: json['status'] as String,
      kycStatus: json['kyc_status'] as String,
    );
  }
}

class CashAccount {
  final String accountId;
  final String? iban;
  final String currency;
  final String currencySymbol;
  final double availableBalance;
  final double pendingBalance;

  const CashAccount({
    required this.accountId,
    this.iban,
    required this.currency,
    this.currencySymbol = '€',
    required this.availableBalance,
    required this.pendingBalance,
  });

  factory CashAccount.fromJson(Map<String, dynamic> json) {
    return CashAccount(
      accountId: json['account_id'] as String,
      iban: json['iban'] as String?,
      currency: json['currency'] as String,
      currencySymbol: json['currency_symbol'] as String? ?? '€',
      availableBalance: double.tryParse(json['available_balance'].toString()) ?? 0,
      pendingBalance: double.tryParse(json['pending_balance'].toString()) ?? 0,
    );
  }
}

class CashTransaction {
  final String id;
  final String type;
  final String? transactionKind;
  final String direction;
  final double amount;
  final String currency;
  final String status;
  final String? externalReference;
  final String? provider;
  final String? remitterName;
  final String? narrative;
  final String createdAt;

  const CashTransaction({
    required this.id,
    required this.type,
    this.transactionKind,
    required this.direction,
    required this.amount,
    required this.currency,
    required this.status,
    this.externalReference,
    this.provider,
    this.remitterName,
    this.narrative,
    required this.createdAt,
  });

  factory CashTransaction.fromJson(Map<String, dynamic> json) {
    return CashTransaction(
      id: json['id'] as String,
      type: json['type'] as String,
      transactionKind: json['transaction_kind'] as String?,
      direction: json['direction'] as String,
      amount: double.tryParse(json['amount'].toString()) ?? 0,
      currency: json['currency'] as String? ?? 'EUR',
      status: json['status'] as String,
      externalReference: json['external_reference'] as String?,
      provider: json['provider'] as String?,
      remitterName: json['remitter_name'] as String?,
      narrative: json['narrative'] as String?,
      createdAt: json['created_at'] as String,
    );
  }
}

class CashData {
  final CashClient client;
  final CashAccount? cashAccount;
  final List<CashTransaction> recentTransactions;
  final String? lastUpdated;

  const CashData({
    required this.client,
    this.cashAccount,
    this.recentTransactions = const [],
    this.lastUpdated,
  });

  factory CashData.fromJson(Map<String, dynamic> json) {
    return CashData(
      client: CashClient.fromJson(json['client'] as Map<String, dynamic>),
      cashAccount: json['cash_account'] != null
          ? CashAccount.fromJson(json['cash_account'] as Map<String, dynamic>)
          : null,
      recentTransactions: (json['recent_transactions'] as List<dynamic>?)
              ?.map((e) => CashTransaction.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      lastUpdated: json['last_updated'] as String?,
    );
  }
}
