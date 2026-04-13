import 'package:flutter/material.dart';

import '../../../../design_system/design_system.dart';

/// Page de dépôt par virement bancaire (depuis la modale Déposer).
class DepositVirementScreen extends StatelessWidget {
  const DepositVirementScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      appBar: AppBar(
        title: const Text('Virement bancaire'),
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
                'Dépôt par virement bancaire',
                style: AppTypography.sectionTitle.copyWith(color: AppColors.textPrimary),
              ),
              const SizedBox(height: AppSpacing.lg),
              Text(
                'Contenu à venir : formulaire ou instructions pour effectuer un virement vers votre compte Vancelian.',
                style: AppTypography.paragraph.copyWith(color: AppColors.textSecondary),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
