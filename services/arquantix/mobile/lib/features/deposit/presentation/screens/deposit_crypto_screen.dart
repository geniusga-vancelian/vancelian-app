import 'package:flutter/material.dart';

import '../../../../design_system/design_system.dart';

/// Page de dépôt par transfert crypto (depuis la modale Déposer).
class DepositCryptoScreen extends StatelessWidget {
  const DepositCryptoScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      appBar: AppBar(
        title: const Text('Transfert crypto'),
        titleTextStyle: AppTypography.sectionTitle,
        backgroundColor: AppColors.cardBackground,
        foregroundColor: AppColors.textPrimary,
        elevation: 0,
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.xl),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Dépôt par transfert crypto',
                style: AppTypography.sectionTitle.copyWith(color: AppColors.textPrimary),
              ),
              const SizedBox(height: AppSpacing.lg),
              Text(
                'Contenu à venir : adresse de portefeuille ou instructions pour transférer des crypto-actifs.',
                style: AppTypography.paragraph.copyWith(color: AppColors.textSecondary),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
