import 'package:flutter/material.dart';

import '../../../../design_system/design_system.dart';

/// Page "Plus" / More.
class MoreScreen extends StatelessWidget {
  const MoreScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.xl),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              AppPageTitle('Plus'),
              const SizedBox(height: AppSpacing.lg),
              Text(
                'Paramètres et autres options à venir.',
                style: AppTypography.meta,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
