class EuroAccountData {
  const EuroAccountData({
    required this.clientId,
    required this.clientEmail,
    this.account,
    this.transactions = const [],
  });

  final String clientId;
  final String clientEmail;
  final EuroAccount? account;
  final List<EuroTransaction> transactions;

  factory EuroAccountData.fromJson(Map<String, dynamic> json) {
    final client = json['client'] as Map<String, dynamic>? ?? {};
    final accountRaw = json['account'] as Map<String, dynamic>?;
    final txsRaw = json['transactions'] as List<dynamic>? ?? [];

    return EuroAccountData(
      clientId: (client['id'] ?? '').toString(),
      clientEmail: (client['email'] ?? '').toString(),
      account: accountRaw != null ? EuroAccount.fromJson(accountRaw) : null,
      transactions: txsRaw
          .whereType<Map<String, dynamic>>()
          .map(EuroTransaction.fromJson)
          .toList(),
    );
  }
}

class EuroAccount {
  const EuroAccount({
    required this.accountId,
    required this.currency,
    required this.currencySymbol,
    required this.balance,
    required this.pendingBalance,
    this.ibanMasked,
    this.accountHolderName,
  });

  final String accountId;
  final String currency;
  final String currencySymbol;
  final String balance;
  final String pendingBalance;
  final String? ibanMasked;
  final String? accountHolderName;

  factory EuroAccount.fromJson(Map<String, dynamic> json) {
    return EuroAccount(
      accountId: (json['account_id'] ?? '').toString(),
      currency: (json['currency'] ?? 'EUR').toString(),
      currencySymbol: (json['currency_symbol'] ?? '€').toString(),
      balance: (json['balance'] ?? '0').toString(),
      pendingBalance: (json['pending_balance'] ?? '0').toString(),
      ibanMasked: json['iban_masked'] as String?,
      accountHolderName: json['account_holder_name'] as String?,
    );
  }
}

class EuroTransaction {
  const EuroTransaction({
    required this.id,
    this.transactionKind,
    required this.transactionType,
    required this.direction,
    required this.amount,
    required this.currency,
    required this.currencySymbol,
    required this.status,
    required this.title,
    required this.subtitle,
    required this.createdAt,
    this.externalReference,
    this.provider,
    this.remitterName,
    this.narrative,
  });

  final String id;
  final String? transactionKind;
  final String transactionType;
  final String direction;
  final String amount;
  final String currency;
  final String currencySymbol;
  final String status;
  final String title;
  final String subtitle;
  final DateTime createdAt;
  final String? externalReference;
  final String? provider;
  final String? remitterName;
  final String? narrative;

  factory EuroTransaction.fromJson(Map<String, dynamic> json) {
    return EuroTransaction(
      id: (json['id'] ?? '').toString(),
      transactionKind: json['transaction_kind'] as String?,
      transactionType: (json['transaction_type'] ?? '').toString(),
      direction: (json['direction'] ?? '').toString(),
      amount: (json['amount'] ?? '0').toString(),
      currency: (json['currency'] ?? 'EUR').toString(),
      currencySymbol: (json['currency_symbol'] ?? '€').toString(),
      status: (json['status'] ?? '').toString(),
      title: (json['title'] ?? '').toString(),
      subtitle: (json['subtitle'] ?? 'Compte Euro').toString(),
      createdAt: DateTime.tryParse(json['created_at']?.toString() ?? '') ??
          DateTime.now(),
      externalReference: json['external_reference'] as String?,
      provider: json['provider'] as String?,
      remitterName: json['remitter_name'] as String?,
      narrative: json['narrative'] as String?,
    );
  }
}
