import 'package:flutter/material.dart';

import 'iban_statement_theme.dart';

/// Account / IBAN / BIC / currency — maps to a definition list in HTML.
class AccountInfoCard extends StatelessWidget {
  const AccountInfoCard({
    super.key,
    required this.currency,
    required this.iban,
    required this.bic,
    required this.accountNumber,
  });

  final String currency;
  final String iban;
  final String bic;
  final String accountNumber;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: IbanStatementTheme.pageBackground,
        borderRadius: BorderRadius.circular(IbanStatementTheme.cardRadius),
      ),
      padding: const EdgeInsets.all(IbanStatementTheme.cardPadding),
      child: Column(
        children: [
          _row('Devise', currency),
          const SizedBox(height: 8),
          _row('IBAN', iban),
          const SizedBox(height: 8),
          _row('BIC / SWIFT', bic),
          const SizedBox(height: 8),
          _row('Numéro de compte', accountNumber),
        ],
      ),
    );
  }

  Widget _row(String label, String value) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: Text(
            label,
            style: IbanStatementTheme.interSemiBold(11, height: 18 / 11),
          ),
        ),
        Text(
          value,
          style: IbanStatementTheme.interRegular(11, height: 18 / 11),
        ),
      ],
    );
  }
}
