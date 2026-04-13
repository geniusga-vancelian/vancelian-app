import 'package:flutter/material.dart';

import 'balance_summary_card.dart';
import 'iban_statement_models.dart';
import 'iban_statement_theme.dart';
import 'statement_footer.dart';
import 'statement_header.dart';
import 'statement_meta_section.dart';
import 'transactions_table.dart';

/// Relevé bancaire IBAN au format A4 (largeur fixe) — composition « document »
/// pour prévisualisation avant rendu PDF (WeasyPrint / HTML).
///
/// Sections (ordre stable, mappage HTML sémantique) :
/// 1. [StatementHeader] — en-tête marque + titre + cartes titulaire / RIB
/// 2. [StatementMetaSection] — période couverte
/// 3. [BalanceSummaryCard] — soldes d’ouverture / clôture
/// 4. [TransactionsTable] — mouvements
/// 5. [StatementFooter] — mentions légales et support
class IbanStatementDocument extends StatelessWidget {
  const IbanStatementDocument({
    super.key,
    required this.data,
  });

  final IbanStatementData data;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: IbanStatementTheme.a4WidthPx,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          StatementHeader(data: data),
          Padding(
            padding: const EdgeInsets.fromLTRB(
              IbanStatementTheme.bodyPaddingH,
              IbanStatementTheme.bodyPaddingV,
              IbanStatementTheme.bodyPaddingH,
              IbanStatementTheme.bodyPaddingV,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                StatementMetaSection(
                  periodStart: data.statementPeriodStart,
                  periodEnd: data.statementPeriodEnd,
                ),
                BalanceSummaryCard(
                  openingBalance: data.openingBalance,
                  closingBalance: data.closingBalance,
                  currency: data.currency,
                ),
                TransactionsTable(
                  transactions: data.transactions,
                  currency: data.currency,
                ),
                const StatementFooter(),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
