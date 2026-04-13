/// Data models for IBAN bank statement document preview.
/// Maps cleanly to future Jinja2/HTML templates (semantic sections).
library;

/// Single ledger line — maps to `<tr>` in HTML.
class IbanStatementTransaction {
  const IbanStatementTransaction({
    required this.date,
    required this.description,
    this.outgoing,
    this.incoming,
    required this.balance,
  });

  final String date;
  final String description;
  final double? outgoing;
  final double? incoming;
  final double balance;
}

/// Full statement payload for the A4 document.
class IbanStatementData {
  const IbanStatementData({
    required this.generatedDate,
    required this.statementPeriodStart,
    required this.statementPeriodEnd,
    required this.accountHolderName,
    required this.accountHolderAddress,
    required this.currency,
    required this.iban,
    required this.bic,
    required this.accountNumber,
    required this.openingBalance,
    required this.closingBalance,
    required this.transactions,
  });

  final String generatedDate;
  final String statementPeriodStart;
  final String statementPeriodEnd;
  final String accountHolderName;
  final String accountHolderAddress;
  final String currency;
  final String iban;
  final String bic;
  final String accountNumber;
  final double openingBalance;
  final double closingBalance;
  final List<IbanStatementTransaction> transactions;
}
