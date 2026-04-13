import 'iban_statement_models.dart';

/// Preview data aligned with Figma `mockStatementData.ts`.
const IbanStatementData mockIbanStatementData = IbanStatementData(
  generatedDate: '10 avril 2026',
  statementPeriodStart: '1 mars 2026',
  statementPeriodEnd: '31 mars 2026',
  accountHolderName: 'Mr John Wick',
  accountHolderAddress: '10 Rue de la Paix, 75002 Paris, France',
  currency: 'EUR',
  iban: 'FR76 3000 4000 0500 0001 2345 678',
  bic: 'BNPAFRPPXXX',
  accountNumber: '00001234567',
  openingBalance: 15420.50,
  /// Doit correspondre au solde de la dernière ligne du tableau.
  closingBalance: 19060.25,
  transactions: [
    IbanStatementTransaction(
      date: '01/03/2026',
      description: 'Virement SEPA - Salaire Mars 2026',
      incoming: 4500.00,
      balance: 19920.50,
    ),
    IbanStatementTransaction(
      date: '02/03/2026',
      description: 'Prélèvement - Loyer Appartement',
      outgoing: 1200.00,
      balance: 18720.50,
    ),
    IbanStatementTransaction(
      date: '03/03/2026',
      description: 'Carte - Monoprix Paris 2ème',
      outgoing: 87.45,
      balance: 18633.05,
    ),
    IbanStatementTransaction(
      date: '05/03/2026',
      description: 'Virement - Remboursement Julien Dupont',
      incoming: 150.00,
      balance: 18783.05,
    ),
    IbanStatementTransaction(
      date: '08/03/2026',
      description: 'Prélèvement - EDF Électricité',
      outgoing: 78.90,
      balance: 18704.15,
    ),
    IbanStatementTransaction(
      date: '10/03/2026',
      description: 'Carte - SNCF Billet TGV Paris-Lyon',
      outgoing: 95.00,
      balance: 18609.15,
    ),
    IbanStatementTransaction(
      date: '12/03/2026',
      description: 'Virement SEPA - Dividendes Actions',
      incoming: 320.50,
      balance: 18929.65,
    ),
    IbanStatementTransaction(
      date: '15/03/2026',
      description: 'Prélèvement - Assurance Habitation AXA',
      outgoing: 42.30,
      balance: 18887.35,
    ),
    IbanStatementTransaction(
      date: '18/03/2026',
      description: 'Carte - Restaurant Le Comptoir',
      outgoing: 68.50,
      balance: 18818.85,
    ),
    IbanStatementTransaction(
      date: '20/03/2026',
      description: 'Virement - Placement compte épargne',
      outgoing: 500.00,
      balance: 18318.85,
    ),
    IbanStatementTransaction(
      date: '22/03/2026',
      description: 'Carte - Fnac Champs-Élysées',
      outgoing: 124.90,
      balance: 18193.95,
    ),
    IbanStatementTransaction(
      date: '25/03/2026',
      description: 'Virement SEPA - Freelance Project Alpha',
      incoming: 850.00,
      balance: 19043.95,
    ),
    IbanStatementTransaction(
      date: '26/03/2026',
      description: 'Prélèvement - Abonnement Netflix',
      outgoing: 15.99,
      balance: 19027.96,
    ),
    IbanStatementTransaction(
      date: '28/03/2026',
      description: 'Carte - Carrefour Market',
      outgoing: 112.71,
      balance: 18915.25,
    ),
    IbanStatementTransaction(
      date: '30/03/2026',
      description: 'Virement - Remboursement frais médicaux',
      incoming: 150.00,
      balance: 19065.25,
    ),
    IbanStatementTransaction(
      date: '31/03/2026',
      description: 'Frais de tenue de compte - Mars 2026',
      outgoing: 5.00,
      balance: 19060.25,
    ),
  ],
);
