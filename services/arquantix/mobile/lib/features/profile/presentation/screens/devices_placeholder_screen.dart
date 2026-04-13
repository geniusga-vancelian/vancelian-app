import 'package:flutter/material.dart';

import '../../../../design_system/design_system.dart';

/// Placeholder — historique d’appareils / sessions (produit futur).
class DevicesPlaceholderScreen extends StatelessWidget {
  const DevicesPlaceholderScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return PageSimpleNavBarTopTitlePageContent(
      pageTitle: 'Appareils',
      content: [
        const SizedBox(height: AppSpacing.xxl),
        Text(
          'Vous pourrez bientôt consulter et gérer les appareils connectés à votre compte.',
          style: AppTypography.paragraph.copyWith(
            color: AppColors.textSecondary,
            height: 1.45,
          ),
        ),
      ],
    );
  }
}
