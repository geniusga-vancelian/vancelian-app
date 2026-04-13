import 'package:flutter/material.dart';

import 'iban_statement_models.dart';
import 'iban_statement_theme.dart';
import 'statement_bank_logo.dart';

/// Section 1 — Top brand band + document title + client & account blocks (Figma header).
/// Semantic mapping: `<header>` + nested identity / RIB cards.
class StatementHeader extends StatelessWidget {
  const StatementHeader({
    super.key,
    required this.data,
  });

  final IbanStatementData data;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: IbanStatementTheme.a4WidthPx,
      color: IbanStatementTheme.headerBand,
      padding: const EdgeInsets.only(
        left: IbanStatementTheme.headerPaddingH,
        right: IbanStatementTheme.headerPaddingH,
        top: IbanStatementTheme.headerPaddingTop,
        bottom: IbanStatementTheme.headerPaddingBottom,
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const StatementBankLogo(),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Relevé de compte bancaire',
                      style: IbanStatementTheme.interSemiBold(
                        28,
                        height: 26 / 28,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Relevé généré le ${data.generatedDate}',
                      style: IbanStatementTheme.interRegular(
                        11,
                        height: 15 / 11,
                        color: IbanStatementTheme.mutedLabel,
                      ),
                    ),
                    Text(
                      'Informations en date du ${data.generatedDate} (UTC)',
                      style: IbanStatementTheme.interRegular(
                        11,
                        height: 15 / 11,
                        color: IbanStatementTheme.mutedLabel,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(width: 40),
          SizedBox(
            width: 290,
            child: Column(
              children: [
                _InfoCard(
                  rows: [
                    _LabeledRow(
                      label: 'Account holder',
                      value: data.accountHolderName,
                      valueBold: true,
                    ),
                    _LabeledRow(
                      label: 'Address',
                      value: data.accountHolderAddress,
                      alignEnd: true,
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                _InfoCard(
                  rows: [
                    _LabeledRow(label: 'Currency', value: data.currency),
                    _LabeledRow(label: 'IBAN', value: data.iban),
                    _LabeledRow(label: 'BIC / SWIFT', value: data.bic),
                    _LabeledRow(label: 'Account Number', value: data.accountNumber),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _InfoCard extends StatelessWidget {
  const _InfoCard({required this.rows});

  final List<Widget> rows;

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
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: _spaceRows(rows, 8),
      ),
    );
  }

  List<Widget> _spaceRows(List<Widget> r, double gap) {
    final out = <Widget>[];
    for (var i = 0; i < r.length; i++) {
      out.add(r[i]);
      if (i < r.length - 1) {
        out.add(SizedBox(height: gap));
      }
    }
    return out;
  }
}

class _LabeledRow extends StatelessWidget {
  const _LabeledRow({
    required this.label,
    required this.value,
    this.valueBold = false,
    this.alignEnd = false,
  });

  final String label;
  final String value;
  final bool valueBold;
  final bool alignEnd;

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: Text(
            label,
            style: IbanStatementTheme.interSemiBold(11, height: 18 / 11),
          ),
        ),
        if (alignEnd)
          SizedBox(
            width: 203,
            child: Text(
              value,
              textAlign: TextAlign.right,
              style: valueBold
                  ? IbanStatementTheme.interBold(11, height: 18 / 11)
                  : IbanStatementTheme.interRegular(11, height: 18 / 11),
            ),
          )
        else
          Text(
            value,
            style: valueBold
                ? IbanStatementTheme.interBold(11, height: 18 / 11)
                : IbanStatementTheme.interRegular(11, height: 18 / 11),
          ),
      ],
    );
  }
}
