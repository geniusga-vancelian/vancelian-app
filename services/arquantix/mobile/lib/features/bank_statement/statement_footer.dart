import 'package:flutter/material.dart';

import 'iban_statement_theme.dart';

/// Legal / support footer — Figma QR placeholder + ACPR-style disclaimers.
class StatementFooter extends StatelessWidget {
  const StatementFooter({super.key});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 42,
                  height: 43,
                  decoration: BoxDecoration(
                    color: IbanStatementTheme.headerBand,
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(color: IbanStatementTheme.borderSubtle),
                  ),
                  alignment: Alignment.center,
                  child: Text(
                    'QR CODE',
                    textAlign: TextAlign.center,
                    style: IbanStatementTheme.interSemiBold(6, height: 1.0).copyWith(
                      color: IbanStatementTheme.mutedLabel,
                      letterSpacing: IbanStatementTheme.letterMicro,
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                SizedBox(
                  width: 200,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Signaler une carte perdue ou volée',
                        style: IbanStatementTheme.interSemiBold(8, height: 11 / 8),
                      ),
                      Text(
                        '+33 1 23 45 67 89',
                        style: IbanStatementTheme.interRegular(8, height: 11 / 8),
                      ),
                      Text(
                        "Obtenir de l'aide dans l'application",
                        style: IbanStatementTheme.interSemiBold(8, height: 11 / 8),
                      ),
                      Text(
                        'Scanner le QR code',
                        style: IbanStatementTheme.interRegular(8, height: 11 / 8),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(width: 40),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    "Vancelian Bank SAS est un établissement de crédit agréé en France sous le numéro d'entreprise 912 345 678 et le code d'autorisation ACPR-2026-001, dont le siège social est situé 10 rue de la Paix, 75002 Paris, France. Vancelian Bank SAS est supervisée par l'Autorité de contrôle prudentiel et de résolution (ACPR) ainsi que par la Banque de France.",
                    style: IbanStatementTheme.interRegular(7, height: 10 / 7),
                  ),
                  const SizedBox(height: 8),
                  Text.rich(
                    TextSpan(
                      style: IbanStatementTheme.interRegular(7, height: 10 / 7),
                      children: [
                        const TextSpan(
                          text:
                              "Les dépôts sont protégés par le Fonds de Garantie des Dépôts et de Résolution (FGDR), dans les limites et conditions prévues par la réglementation en vigueur. Certaines exceptions peuvent s'appliquer. Pour plus d'informations, veuillez consulter le site officiel du FGDR. ",
                        ),
                        TextSpan(
                          text:
                              "Si vous avez des questions, veuillez nous contacter via la messagerie intégrée à l'application Vancelian.",
                          style: IbanStatementTheme.interSemiBold(7, height: 10 / 7),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
        const SizedBox(height: 10),
        Row(
          children: [
            Expanded(
              child: Text(
                '© 2026 Vancelian Bank SAS – Tous droits réservés',
                style: IbanStatementTheme.interRegular(8, height: 11 / 8),
              ),
            ),
            Text(
              '1/1',
              textAlign: TextAlign.right,
              style: IbanStatementTheme.interRegular(8, height: 11 / 8),
            ),
          ],
        ),
      ],
    );
  }
}
