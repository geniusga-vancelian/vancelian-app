class IbanDetails {
  const IbanDetails({
    required this.accountHolderName,
    this.iban,
    this.bic,
    this.currency = 'EUR',
    this.currencySymbol = '€',
  });

  final String accountHolderName;
  final String? iban;
  final String? bic;
  final String currency;
  final String currencySymbol;

  factory IbanDetails.fromJson(Map<String, dynamic> json) {
    return IbanDetails(
      accountHolderName: (json['account_holder_name'] ?? '').toString(),
      iban: json['iban'] as String?,
      bic: json['bic'] as String?,
      currency: (json['currency'] ?? 'EUR').toString(),
      currencySymbol: (json['currency_symbol'] ?? '€').toString(),
    );
  }
}
