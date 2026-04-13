import 'package:flutter/material.dart';

import '../../../../design_system/design_system.dart';

/// Page de dépôt par carte bancaire (depuis la modale Déposer).
class DepositCarteScreen extends StatelessWidget {
  const DepositCarteScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      appBar: AppBar(
        title: const Text('Carte bancaire'),
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
                'Dépôt par carte bancaire',
                style: AppTypography.sectionTitle.copyWith(color: AppColors.textPrimary),
              ),
              const SizedBox(height: AppSpacing.lg),
              Text(
                'Contenu à venir : formulaire de saisie de carte pour déposer des fonds.',
                style: AppTypography.paragraph.copyWith(color: AppColors.textSecondary),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
