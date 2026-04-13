import 'package:flutter/material.dart';

import 'iban_statement_formatting.dart';
import 'iban_statement_theme.dart';

/// Opening / closing balances — Figma gray card.
class BalanceSummaryCard extends StatelessWidget {
  const BalanceSummaryCard({
    super.key,
    required this.openingBalance,
    required this.closingBalance,
    required this.currency,
  });

  final double openingBalance;
  final double closingBalance;
  final String currency;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 20),
      decoration: BoxDecoration(
        color: IbanStatementTheme.headerBand,
        borderRadius: BorderRadius.circular(IbanStatementTheme.cardRadius),
      ),
      padding: const EdgeInsets.all(IbanStatementTheme.cardPadding),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Soldes du compte',
            style: IbanStatementTheme.interSemiBold(14, height: 18 / 14),
          ),
          const SizedBox(height: 10),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    "SOLDE D'OUVERTURE",
                    style: IbanStatementTheme.interSemiBold(
                      9,
                      height: 18 / 9,
                    ).copyWith(
                      fontWeight: FontWeight.w600,
                      letterSpacing: IbanStatementTheme.letterTight,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '${formatStatementAmount(openingBalance)} $currency',
                    style: IbanStatementTheme.interRegular(11, height: 18 / 11),
                  ),
                ],
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                    'SOLDE DE CLÔTURE',
                    style: IbanStatementTheme.interSemiBold(
                      9,
                      height: 18 / 9,
                    ).copyWith(
                      fontWeight: FontWeight.w600,
                      letterSpacing: IbanStatementTheme.letterTight,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '${formatStatementAmount(closingBalance)} $currency',
                    style: IbanStatementTheme.interRegular(11, height: 18 / 11),
                  ),
                ],
              ),
            ],
          ),
        ],
      ),
    );
  }
}
