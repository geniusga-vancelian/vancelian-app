import 'package:flutter/material.dart';

import '../../../design_system/components/setup_progress_card.dart';
import '../../profile/data/mobile_app_profile.dart';
import 'registration_flow_step_info.dart';

/// Données prêtes pour [RegistrationProgressModule] / [SetupProgressCard].
class RegistrationProgressModuleData {
  const RegistrationProgressModuleData({
    required this.currentStep,
    required this.totalSteps,
    required this.title,
    this.subtitle,
    required this.steps,
    required this.canContinue,
  });

  final int currentStep;
  final int totalSteps;
  final String title;
  final String? subtitle;
  final List<SetupStep> steps;
  final bool canContinue;
}

/// Construit progression, sous-titre et liste d’étapes à partir du profil
/// (champs dérivés backend) et des étapes du flux actif.
class RegistrationProgressModuleBuilder {
  RegistrationProgressModuleBuilder._();

  static int totalForCard({
    MobileAppProfile? profile,
    required List<RegistrationFlowStepInfo> flowSteps,
  }) {
    final t = profile?.registrationDerivedTotalCount;
    if (t != null && t > 0) return t;
    return flowSteps.isNotEmpty ? flowSteps.length : 12;
  }

  static int currentStepForCard({
    MobileAppProfile? profile,
    required List<RegistrationFlowStepInfo> flowSteps,
  }) {
    final done = profile?.registrationDerivedCompletedCount;
    final total = profile?.registrationDerivedTotalCount;
    if (done != null && total != null && total > 0) {
      return (done + 1).clamp(1, total);
    }
    return 1;
  }

  static String? buildSubtitle({
    String? jurisdictionName,
    String? flowName,
    int? flowVersion,
    MobileAppProfile? profile,
  }) {
    final subtitle = StringBuffer();
    if (jurisdictionName != null) subtitle.write(jurisdictionName);
    if (flowName != null) {
      if (subtitle.isNotEmpty) subtitle.write(' — ');
      subtitle.write(flowName);
      if (flowVersion != null) subtitle.write(' v$flowVersion');
    }
    if (profile?.registrationDerivedNextStepLabel != null) {
      if (subtitle.isNotEmpty) subtitle.write('\n');
      subtitle.write(
        'Prochaine étape : ${profile!.registrationDerivedNextStepLabel}',
      );
    }
    return subtitle.isNotEmpty ? subtitle.toString() : null;
  }

  static IconData iconForStep(String stepKey) {
    final k = stepKey.toLowerCase();
    if (k.contains('personal') ||
        k.contains('info') ||
        k.contains('identity')) {
      return Icons.person_outline_rounded;
    }
    if (k.contains('residen') || k.contains('address')) {
      return Icons.location_on_outlined;
    }
    if (k.contains('consent') ||
        k.contains('legal') ||
        k.contains('terms')) {
      return Icons.gavel_outlined;
    }
    if (k.contains('document') || k.contains('upload')) {
      return Icons.upload_file_outlined;
    }
    if (k.contains('financial') ||
        k.contains('income') ||
        k.contains('employment')) {
      return Icons.account_balance_outlined;
    }
    return Icons.flag_outlined;
  }

  static List<SetupStep> buildSetupSteps({
    required MobileAppProfile? profile,
    required List<RegistrationFlowStepInfo> flowSteps,
    required bool canContinue,
    required VoidCallback onNavigate,
  }) {
    final derivedDone = profile?.registrationDerivedCompletedCount;

    if (flowSteps.isEmpty) {
      return [
        SetupStep(
          title: 'Vérifier votre identité',
          subtitle: 'Accédez à l’ensemble des services',
          status: SetupStepStatus.completed,
          onTap: canContinue ? onNavigate : null,
        ),
        SetupStep(
          title: 'Étape suivante',
          subtitle: 'Compléter l’inscription',
          tag: 'Requis',
          status: SetupStepStatus.inProgress,
          onTap: canContinue ? onNavigate : null,
        ),
        SetupStep(
          title: 'Dernière ligne',
          subtitle: 'Informations complémentaires',
          status: SetupStepStatus.pending,
          icon: Icons.photo_library_outlined,
          onTap: canContinue ? onNavigate : null,
        ),
      ];
    }

    final totalD = profile?.registrationDerivedTotalCount;
    final alignDerived =
        derivedDone != null && totalD != null && totalD == flowSteps.length;

    return flowSteps.asMap().entries.map((entry) {
      final i = entry.key;
      final step = entry.value;

      SetupStepStatus status;
      if (alignDerived) {
        final d = derivedDone;
        if (i < d) {
          status = SetupStepStatus.completed;
        } else if (i == d) {
          status = SetupStepStatus.inProgress;
        } else {
          status = SetupStepStatus.pending;
        }
      } else {
        if (i == 0) {
          status = SetupStepStatus.completed;
        } else if (i == 1) {
          status = SetupStepStatus.inProgress;
        } else {
          status = SetupStepStatus.pending;
        }
      }

      return SetupStep(
        title: step.title,
        subtitle: step.description ?? 'Compléter cette étape',
        tag: i == 1 ? (step.isBlocking ? 'Requis' : 'Optionnel') : null,
        status: status,
        icon: iconForStep(step.stepKey),
        onTap: canContinue ? onNavigate : null,
      );
    }).toList();
  }

  static RegistrationProgressModuleData build({
    required MobileAppProfile? profile,
    required List<RegistrationFlowStepInfo> flowSteps,
    String? jurisdictionName,
    String? flowName,
    int? flowVersion,
    required bool canLaunch,
    required VoidCallback onNavigate,
    String title = 'Finalisez votre inscription',
  }) {
    final current = currentStepForCard(profile: profile, flowSteps: flowSteps);
    final total = totalForCard(profile: profile, flowSteps: flowSteps);
    final steps = buildSetupSteps(
      profile: profile,
      flowSteps: flowSteps,
      canContinue: canLaunch,
      onNavigate: onNavigate,
    );
    final subtitle = buildSubtitle(
      jurisdictionName: jurisdictionName,
      flowName: flowName,
      flowVersion: flowVersion,
      profile: profile,
    );
    return RegistrationProgressModuleData(
      currentStep: current,
      totalSteps: total,
      title: title,
      subtitle: subtitle,
      steps: steps,
      canContinue: canLaunch,
    );
  }
}
