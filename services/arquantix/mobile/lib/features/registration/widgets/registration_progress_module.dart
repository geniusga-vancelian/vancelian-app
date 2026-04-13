import 'package:flutter/material.dart';

import '../../../design_system/components/setup_progress_card.dart';
import 'registration_progress_module_builder.dart';

/// Module unique « parcours d’inscription » (anneau, titre, sous-titre, CTA, liste
/// d’étapes) — même rendu que le hub Registration, réutilisable sur la Home.
class RegistrationProgressModule extends StatelessWidget {
  const RegistrationProgressModule({
    super.key,
    required this.data,
    required this.onContinue,
    this.ctaLabel = 'Continuer',
  });

  final RegistrationProgressModuleData data;
  final VoidCallback onContinue;
  final String ctaLabel;

  @override
  Widget build(BuildContext context) {
    return SetupProgressCard(
      currentStep: data.currentStep,
      totalSteps: data.totalSteps,
      title: data.title,
      subtitle: data.subtitle,
      ctaLabel: ctaLabel,
      onCtaPressed: data.canContinue ? onContinue : null,
      steps: data.steps,
    );
  }
}
