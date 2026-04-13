/// Parcours d’activation (Home) — aligné sur ``activation_journey`` du profil API (v3).

/// États UX par étape (source serveur).
enum ActivationStageUxStatus {
  locked,
  available,
  inProgress,
  completed;

  static ActivationStageUxStatus parse(String? raw) {
    final s = (raw ?? '').trim().toLowerCase();
    switch (s) {
      case 'completed':
      case 'complete':
      case 'done':
        return ActivationStageUxStatus.completed;
      case 'in_progress':
        return ActivationStageUxStatus.inProgress;
      case 'available':
        return ActivationStageUxStatus.available;
      case 'locked':
        return ActivationStageUxStatus.locked;
      case 'pending':
        return ActivationStageUxStatus.inProgress;
      default:
        return ActivationStageUxStatus.locked;
    }
  }
}

class ActivationJourneyStage {
  const ActivationJourneyStage({
    required this.key,
    required this.id,
    required this.uxStatus,
    required this.weight,
    required this.isNextStep,
    required this.title,
    required this.subtitle,
    required this.ctaLabel,
    required this.targetRoute,
  });

  final String key;
  final String id;
  final ActivationStageUxStatus uxStatus;
  final double weight;
  final bool isNextStep;
  final String title;
  final String subtitle;
  final String ctaLabel;
  final String targetRoute;

  bool get isComplete => uxStatus == ActivationStageUxStatus.completed;

  factory ActivationJourneyStage.fromJson(Map<String, dynamic> json) {
    final statusRaw =
        json['ux_status'] ?? json['status'] ?? json['uxStatus'];
    final legacy = statusRaw?.toString().trim().toLowerCase() ?? '';
    var ux = ActivationStageUxStatus.parse(statusRaw?.toString());
    if (legacy == 'pending') {
      ux = ActivationStageUxStatus.inProgress;
    }
    return ActivationJourneyStage(
      key: (json['key'] ?? json['id'] ?? '').toString(),
      id: (json['id'] ?? '').toString(),
      uxStatus: ux,
      weight: _weight(json['weight']),
      isNextStep: json['is_next_step'] == true,
      title: (json['title'] ?? '').toString(),
      subtitle: (json['subtitle'] ?? '').toString(),
      ctaLabel: (json['cta_label'] ?? '').toString(),
      targetRoute: (json['target_route'] ?? '').toString(),
    );
  }

  static double _weight(Object? raw) {
    if (raw is num) return raw.toDouble();
    return double.tryParse('$raw') ?? 0;
  }
}

class ActivationJourney {
  const ActivationJourney({
    required this.configVersion,
    required this.showModule,
    this.activationComplete = false,
    this.completionMessage,
    required this.weightedProgressPercent,
    required this.headline,
    required this.heroSubtitle,
    this.heroImageUrl,
    required this.remainingStepsMessage,
    this.primaryCtaLabel,
    this.primaryCtaTargetRoute,
    required this.stages,
  });

  final int configVersion;
  final bool showModule;
  /// Les 3 étapes sont terminées (backend).
  final bool activationComplete;
  /// Libellé court affichable quand [showModule] est false (ex. « Compte activé »).
  final String? completionMessage;
  final int weightedProgressPercent;
  final String headline;
  final String heroSubtitle;
  final String? heroImageUrl;
  final String remainingStepsMessage;
  final String? primaryCtaLabel;
  final String? primaryCtaTargetRoute;
  final List<ActivationJourneyStage> stages;

  factory ActivationJourney.fromJson(Map<String, dynamic> json) {
    final rawStages = json['stages'];
    final stages = <ActivationJourneyStage>[];
    if (rawStages is List) {
      for (final e in rawStages) {
        if (e is Map<String, dynamic>) {
          stages.add(ActivationJourneyStage.fromJson(e));
        }
      }
    }
    final wp = json['weighted_progress_percent'];
    var pct = 0;
    if (wp is int) {
      pct = wp.clamp(0, 100);
    } else if (wp is num) {
      pct = wp.round().clamp(0, 100);
    }
    final rawHeroImg = json['hero_image_url']?.toString().trim();
    return ActivationJourney(
      configVersion: json['config_version'] is int
          ? json['config_version'] as int
          : int.tryParse('${json['config_version']}') ?? 1,
      showModule: json['show_module'] == true,
      activationComplete: json['activation_complete'] == true,
      completionMessage: json['completion_message']?.toString(),
      weightedProgressPercent: pct,
      headline: (json['headline'] ?? 'Trois étapes pour investir en toute confiance')
          .toString(),
      heroSubtitle: (json['hero_subtitle'] ?? '').toString(),
      heroImageUrl: (rawHeroImg != null && rawHeroImg.isNotEmpty)
          ? rawHeroImg
          : null,
      remainingStepsMessage:
          (json['remaining_steps_message'] ?? '').toString(),
      primaryCtaLabel: json['primary_cta_label']?.toString(),
      primaryCtaTargetRoute: json['primary_cta_target_route']?.toString(),
      stages: stages,
    );
  }
}
