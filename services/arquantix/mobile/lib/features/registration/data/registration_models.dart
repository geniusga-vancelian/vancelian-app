/// Data models for the Registration Flow runtime API.
///
/// All models parse null-safely from the backend JSON contract:
/// POST /sessions/start, GET /sessions/{id}/screen, POST /submit, etc.

class RegistrationComponent {
  final String id;
  final String componentType;
  final String componentKey;
  final int position;
  final Map<String, dynamic> props;
  final String? bindingSlug;
  final String? fieldDefinitionId;
  final Map<String, dynamic>? validationRule;

  const RegistrationComponent({
    required this.id,
    required this.componentType,
    required this.componentKey,
    required this.position,
    required this.props,
    this.bindingSlug,
    this.fieldDefinitionId,
    this.validationRule,
  });

  factory RegistrationComponent.fromJson(Map<String, dynamic> json) {
    return RegistrationComponent(
      id: json['id'] as String? ?? '',
      componentType: json['component_type'] as String? ?? '',
      componentKey: json['component_key'] as String? ?? '',
      position: json['position'] as int? ?? 0,
      props: json['props'] is Map
          ? Map<String, dynamic>.from(json['props'] as Map)
          : {},
      bindingSlug: json['binding_slug'] as String?,
      fieldDefinitionId: json['field_definition_id'] as String?,
      validationRule: json['validation'] is Map
          ? Map<String, dynamic>.from(json['validation'] as Map)
          : null,
    );
  }

  String get label => props['label'] as String? ?? '';
  bool get isRequired => props['required'] as bool? ?? false;

  /// Si true : pas de sous-libellé au-dessus de la liste (titre d’écran suffit).
  bool get hideInlineLabel => props['hide_inline_label'] == true;
  String? get placeholder => props['placeholder'] as String?;
  List<Map<String, dynamic>> get options {
    final raw = props['options'];
    if (raw is List) return raw.cast<Map<String, dynamic>>();
    return [];
  }
}

class RegistrationScreen {
  final String id;
  final String screenKey;
  final String title;
  final String? subtitle;
  final String? buttonLabel;
  final String layoutType;
  final String screenType;
  final String? interactionType;
  /// Options écran (admin) — ex. `phone_confirm_modal_enabled` pour la modale mobile.
  final Map<String, dynamic>? config;
  final Map<String, dynamic>? interactionConfig;
  final Map<String, dynamic>? interactionPayload;
  final List<RegistrationComponent> components;

  const RegistrationScreen({
    required this.id,
    required this.screenKey,
    required this.title,
    this.subtitle,
    this.buttonLabel,
    required this.layoutType,
    this.screenType = 'form',
    this.interactionType,
    this.config,
    this.interactionConfig,
    this.interactionPayload,
    required this.components,
  });

  /// Modale « confirmer le numéro » sur l’app (désactivable depuis l’admin).
  /// Défaut `true` si la clé est absente.
  bool get phoneConfirmModalEnabled {
    final v = config?['phone_confirm_modal_enabled'];
    if (v is bool) return v;
    return true;
  }

  /// Écran `screen_type: permission_prompt` (Face ID / notifications).
  bool get isPermissionPromptScreen => screenType == 'permission_prompt';

  /// `face_id` ou `push_notifications` (config admin).
  String? get permissionKind => config?['permission_kind'] as String?;

  /// Slug enregistré en `true` / `false` au « Valider » (bouton primaire / secondaire).
  String? get permissionDecisionSlug => config?['decision_slug'] as String?;

  /// Après [completeSession] réussi — modale succès (ex. financial profile), pas un écran dédié.
  bool get showSuccessModalOnComplete =>
      config?['show_success_modal_on_complete'] == true;

  /// Sous-objet optionnel : `title`, `description`, `primary_label`.
  Map<String, dynamic>? get successModalConfig {
    final m = config?['success_modal'];
    if (m is Map<String, dynamic>) return m;
    if (m is Map) return Map<String, dynamic>.from(m);
    return null;
  }

  /// Libellé bouton secondaire (refus / plus tard).
  String get permissionSecondaryButtonLabel {
    final s = config?['secondary_button_label'] as String?;
    if (s == null || s.trim().isEmpty) return 'Not Now';
    return s.trim();
  }

  factory RegistrationScreen.fromJson(Map<String, dynamic> json) {
    final rawComponents = json['components'] as List<dynamic>? ?? [];
    Map<String, dynamic>? asMap(dynamic v) {
      if (v is Map) {
        return Map<String, dynamic>.fromEntries(
          v.entries.map((e) => MapEntry(e.key.toString(), e.value)),
        );
      }
      return null;
    }

    return RegistrationScreen(
      id: json['id'] as String? ?? '',
      screenKey: json['screen_key'] as String? ?? '',
      title: json['title'] as String? ?? '',
      subtitle: json['subtitle'] as String?,
      buttonLabel: json['button_label'] as String?,
      layoutType: json['layout_type'] as String? ?? 'form',
      screenType: json['screen_type'] as String? ?? 'form',
      interactionType: json['interaction_type'] as String?,
      config: asMap(json['config']),
      interactionConfig: asMap(json['interaction_config']),
      interactionPayload: asMap(json['interaction_payload']),
      components: rawComponents
          .whereType<Map<String, dynamic>>()
          .map(RegistrationComponent.fromJson)
          .toList(),
    );
  }
}

class RegistrationStep {
  final String id;
  final String stepKey;
  final String title;
  final String? description;
  final bool isBlocking;
  final String status;

  const RegistrationStep({
    required this.id,
    required this.stepKey,
    required this.title,
    this.description,
    required this.isBlocking,
    required this.status,
  });

  factory RegistrationStep.fromJson(Map<String, dynamic> json) {
    return RegistrationStep(
      id: json['id'] as String? ?? '',
      stepKey: json['step_key'] as String? ?? '',
      title: json['title'] as String? ?? '',
      description: json['description'] as String?,
      isBlocking: json['is_blocking'] as bool? ?? true,
      status: json['status'] as String? ?? 'not_started',
    );
  }
}

class RegistrationStepState {
  final String stepId;
  final String status;
  final String? startedAt;
  final String? completedAt;

  const RegistrationStepState({
    required this.stepId,
    required this.status,
    this.startedAt,
    this.completedAt,
  });

  factory RegistrationStepState.fromJson(Map<String, dynamic> json) {
    return RegistrationStepState(
      stepId: json['step_id'] as String? ?? '',
      status: json['status'] as String? ?? 'not_started',
      startedAt: json['started_at'] as String?,
      completedAt: json['completed_at'] as String?,
    );
  }
}

/// Parsed response from screen-returning endpoints
/// (start, get_screen, submit, next, prev).
class RegistrationSessionState {
  final String sessionId;
  final String status;
  final int flowVersion;
  final double progressPercent;
  final bool isLastScreen;
  final RegistrationStep? currentStep;
  final String? currentStepStatus;
  final RegistrationScreen? screen;
  final Map<String, dynamic> collectedData;
  final List<RegistrationStepState> stepStates;

  /// Aligné sur l’API (`is_first_screen`) : premier écran **du step courant** (pas du flux entier).
  final bool? isFirstScreenFromPayload;

  const RegistrationSessionState({
    required this.sessionId,
    required this.status,
    required this.flowVersion,
    required this.progressPercent,
    required this.isLastScreen,
    this.currentStep,
    this.currentStepStatus,
    this.screen,
    required this.collectedData,
    required this.stepStates,
    this.isFirstScreenFromPayload,
  });

  bool get isFirstScreen =>
      isFirstScreenFromPayload ?? (progressPercent == 0);
  bool get isCompleted => status == 'completed';

  factory RegistrationSessionState.fromJson(Map<String, dynamic> json) {
    final stepJson = json['current_step'] as Map<String, dynamic>?;
    final screenJson = json['screen'] as Map<String, dynamic>?;
    final rawStates = json['step_states'] as List<dynamic>? ?? [];
    final rawCollected = json['collected_data'] as Map<String, dynamic>? ?? {};

    return RegistrationSessionState(
      sessionId: json['session_id'] as String? ?? '',
      status: json['status'] as String? ?? 'in_progress',
      flowVersion: json['flow_version'] as int? ?? 1,
      progressPercent:
          (json['progress_percent'] as num?)?.toDouble() ?? 0,
      isLastScreen: json['is_last_screen'] as bool? ?? false,
      isFirstScreenFromPayload: json['is_first_screen'] as bool?,
      currentStep:
          stepJson != null ? RegistrationStep.fromJson(stepJson) : null,
      currentStepStatus: json['current_step_status'] as String?,
      screen:
          screenJson != null ? RegistrationScreen.fromJson(screenJson) : null,
      collectedData: Map<String, dynamic>.from(rawCollected),
      stepStates: rawStates
          .whereType<Map<String, dynamic>>()
          .map(RegistrationStepState.fromJson)
          .toList(),
    );
  }
}
