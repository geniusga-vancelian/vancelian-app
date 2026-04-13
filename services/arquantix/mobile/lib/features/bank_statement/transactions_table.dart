import 'package:flutter/material.dart';

import 'iban_statement_formatting.dart';
import 'iban_statement_models.dart';
import 'iban_statement_theme.dart';

/// Operations table — maps 1:1 to `<table><thead><tbody>` in HTML / Jinja.
class TransactionsTable extends StatelessWidget {
  const TransactionsTable({
    super.key,
    required this.transactions,
    required this.currency,
  });

  final List<IbanStatementTransaction> transactions;
  final String currency;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 40),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Opérations',
            style: IbanStatementTheme.interSemiBold(14, height: 18 / 14),
          ),
          const SizedBox(height: 12),
          Container(
            width: double.infinity,
            decoration: BoxDecoration(
              color: IbanStatementTheme.pageBackground,
              borderRadius: BorderRadius.circular(IbanStatementTheme.cardRadius),
            ),
            clipBehavior: Clip.antiAlias,
            child: Table(
              columnWidths: const {
                0: FixedColumnWidth(88),
                1: FlexColumnWidth(1),
                2: FixedColumnWidth(92),
                3: FixedColumnWidth(92),
                4: FixedColumnWidth(104),
              },
              defaultVerticalAlignment: TableCellVerticalAlignment.top,
              children: [
                TableRow(
                  decoration: const BoxDecoration(
                    border: Border(
                      bottom: BorderSide(color: IbanStatementTheme.tableHeaderRule),
                    ),
                  ),
                  children: [
                    _th('Date', leftPad: 20),
                    _th('Description'),
                    _th('Débit', right: true),
                    _th('Crédit', right: true),
                    _th('Solde', right: true, rightPad: 20),
                  ],
                ),
                for (var i = 0; i < transactions.length; i++)
                  TableRow(
                    decoration: const BoxDecoration(
                      border: Border(
                        top: BorderSide(color: IbanStatementTheme.borderSubtle),
                      ),
                    ),
                    children: [
                      _tdDate(transactions[i].date, leftPad: 20),
                      _tdDesc(transactions[i].description),
                      _tdMoneyDebit(transactions[i].outgoing, currency),
                      _tdMoneyCredit(transactions[i].incoming, currency),
                      _tdMoneyBalance(transactions[i].balance, currency, rightPad: 20),
                    ],
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _th(String t, {bool right = false, double leftPad = 0, double rightPad = 0}) {
    return Padding(
      padding: EdgeInsets.fromLTRB(leftPad, 10, rightPad, 10),
      child: Text(
        t.toUpperCase(),
        textAlign: right ? TextAlign.right : TextAlign.left,
        style: IbanStatementTheme.interSemiBold(9, height: 18 / 9).copyWith(
          letterSpacing: IbanStatementTheme.letterTight,
        ),
      ),
    );
  }

  Widget _tdDate(String t, {double leftPad = 0}) {
    return Padding(
      padding: EdgeInsets.fromLTRB(leftPad, 10, 0, 10),
      child: Text(
        t,
        style: IbanStatementTheme.interRegular(11, height: 18 / 11),
      ),
    );
  }

  Widget _tdDesc(String t) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 10),
      child: Text(
        t,
        softWrap: true,
        style: IbanStatementTheme.interRegular(11, height: 18 / 11),
      ),
    );
  }

  Widget _tdMoneyDebit(double? outgoing, String cur) {
    final text = outgoing == null
        ? ''
        : '-${formatStatementAmount(outgoing)} $cur';
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 10),
      child: Text(
        text,
        textAlign: TextAlign.right,
        style: IbanStatementTheme.interRegular(11, height: 18 / 11),
      ),
    );
  }

  Widget _tdMoneyCredit(double? incoming, String cur) {
    final text = incoming == null
        ? ''
        : '+${formatStatementAmount(incoming)} $cur';
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 10),
      child: Text(
        text,
        textAlign: TextAlign.right,
        style: IbanStatementTheme.interRegular(11, height: 18 / 11),
      ),
    );
  }

  Widget _tdMoneyBalance(double balance, String cur, {double rightPad = 0}) {
    return Padding(
      padding: EdgeInsets.fromLTRB(0, 10, rightPad, 10),
      child: Text(
        '${formatStatementAmount(balance)} $cur',
        textAlign: TextAlign.right,
        style: IbanStatementTheme.interRegular(11, height: 18 / 11),
      ),
    );
  }
}
