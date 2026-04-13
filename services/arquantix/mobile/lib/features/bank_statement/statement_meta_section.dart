import 'package:flutter/material.dart';

import 'iban_statement_theme.dart';

/// Period subtitle in the white body (under header) — Figma `h2` line.
/// Maps to a single semantic `<h2>` in HTML.
class StatementMetaSection extends StatelessWidget {
  const StatementMetaSection({
    super.key,
    required this.periodStart,
    required this.periodEnd,
  });

  final String periodStart;
  final String periodEnd;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 20),
      child: Text(
        'Relevé de compte · $periodStart au $periodEnd',
        style: IbanStatementTheme.interSemiBold(14, height: 18 / 14),
      ),
    );
  }
}
