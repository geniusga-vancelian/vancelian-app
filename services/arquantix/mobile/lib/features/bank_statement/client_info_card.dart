import 'package:flutter/material.dart';

import 'iban_statement_theme.dart';

/// Standalone client block (French labels) — usable if layout splits from header.
/// Figma alternate `ClientInformationSection` uses French copy.
class ClientInfoCard extends StatelessWidget {
  const ClientInfoCard({
    super.key,
    required this.name,
    required this.address,
  });

  final String name;
  final String address;

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
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Text(
                  'Titulaire du compte',
                  style: IbanStatementTheme.interSemiBold(11, height: 18 / 11),
                ),
              ),
              Text(
                name,
                style: IbanStatementTheme.interBold(11, height: 18 / 11),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Text(
                  'Adresse',
                  style: IbanStatementTheme.interSemiBold(11, height: 18 / 11),
                ),
              ),
              SizedBox(
                width: 203,
                child: Text(
                  address,
                  textAlign: TextAlign.right,
                  style: IbanStatementTheme.interRegular(11, height: 18 / 11),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
