import 'package:flutter/material.dart';

import 'iban_statement_document.dart';
import 'iban_statement_models.dart';
import 'iban_statement_theme.dart';
import 'mock_iban_statement_data.dart';

/// Écran minimal : fond gris, document centré, défilement vertical uniquement.
/// Pas de barre d’app, pas de navigation — prévisualisation du gabarit imprimable.
class IbanStatementPreviewPage extends StatelessWidget {
  const IbanStatementPreviewPage({
    super.key,
    this.data = mockIbanStatementData,
  });

  final IbanStatementData data;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: IbanStatementTheme.headerBand,
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(vertical: 24),
          child: Container(
            decoration: BoxDecoration(
              color: IbanStatementTheme.pageBackground,
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.08),
                  blurRadius: 24,
                  offset: const Offset(0, 8),
                ),
              ],
            ),
            child: IbanStatementDocument(data: data),
          ),
        ),
      ),
    );
  }
}
