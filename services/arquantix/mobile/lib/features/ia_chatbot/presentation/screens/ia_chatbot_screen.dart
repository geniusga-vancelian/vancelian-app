import 'package:flutter/material.dart';

import '../../../../design_system/design_system.dart';

/// Page chatbot IA pour investir (placeholder).
class IAChatbotScreen extends StatelessWidget {
  const IAChatbotScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      appBar: AppBar(
        title: const Text('IA Investissement'),
        backgroundColor: AppColors.cardBackground,
        foregroundColor: AppColors.textPrimary,
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.xl),
          child: Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(Icons.smart_toy_outlined, size: 64, color: AppColors.accent),
                const SizedBox(height: AppSpacing.lg),
                Text(
                  'Chatbot IA pour investir',
                  style: AppTypography.sectionTitle,
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: AppSpacing.sm),
                Text(
                  'À venir.',
                  style: AppTypography.meta,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
