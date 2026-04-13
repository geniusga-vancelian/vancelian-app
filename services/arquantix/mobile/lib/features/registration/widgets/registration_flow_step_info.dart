/// Étape du flux d’inscription telle que renvoyée par l’API active flow.
class RegistrationFlowStepInfo {
  const RegistrationFlowStepInfo({
    required this.title,
    required this.stepKey,
    required this.isBlocking,
    this.description,
  });

  final String title;
  final String? description;
  final String stepKey;
  final bool isBlocking;

  static List<RegistrationFlowStepInfo> fromFlowJson(
    Map<String, dynamic> flow,
  ) {
    final rawSteps = flow['steps'] as List<dynamic>? ?? [];
    return rawSteps.whereType<Map<String, dynamic>>().map((s) {
      return RegistrationFlowStepInfo(
        title: s['title'] as String? ?? s['step_key'] as String? ?? '',
        description: s['description'] as String?,
        stepKey: s['step_key'] as String? ?? '',
        isBlocking: s['is_blocking'] as bool? ?? true,
      );
    }).toList();
  }
}
