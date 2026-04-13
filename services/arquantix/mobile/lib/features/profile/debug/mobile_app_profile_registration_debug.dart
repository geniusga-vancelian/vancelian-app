import 'package:flutter/foundation.dart';

import '../data/mobile_app_profile.dart';

/// Logs terminal (mode debug uniquement) pour diagnostiquer l’affichage du module
/// d’inscription sur la Home (`shouldShowRegistrationResume` + champs API).
void debugLogMobileAppProfileRegistration({
  required String tag,
  MobileAppProfile? profile,
  String? extra,
}) {
  if (!kDebugMode) return;
  final extraLine = extra != null && extra.isNotEmpty ? ' | $extra' : '';
  final buf = StringBuffer()
    ..writeln('[Registration] ═══ $tag$extraLine');
  if (profile == null) {
    buf.writeln(
      '  profile=null → pas de module (GET /api/mobile/flutter/profile '
      'échoué, corps non-JSON, parse erreur, ou appel non effectué).',
    );
    debugPrint(buf.toString());
    return;
  }

  final p = profile;
  final show = p.shouldShowRegistrationResume;
  buf
    ..writeln(
      '  identité: email=${p.email} initials=${p.initials} '
      'jurisdiction=${p.jurisdiction}',
    )
    ..writeln(
      '  statuts: client_status=${p.clientStatus} kyc_status=${p.kycStatus}',
    )
    ..writeln(
      '  ▶ shouldShowRegistrationResume=$show '
      '(si false, le module Home est masqué)',
    )
    ..writeln(
      '  canonique: registration_completion_ratio=${p.registrationCompletionRatio} '
      'macro=${p.registrationMacroStage} label=${p.registrationMacroLabel}',
    );
  final missing = p.registrationMissingSteps;
  buf.writeln(
    '  missing_steps: count=${missing?.length ?? 0} '
    'sample=${missing == null || missing.isEmpty ? "—" : missing.take(6).join(",")}',
  );
  buf
    ..writeln(
      '  dérivé (collected): ${p.registrationDerivedCompletedCount}/'
      '${p.registrationDerivedTotalCount} '
      'progress_percent=${p.registrationDerivedProgressPercent} '
      'next_key=${p.registrationDerivedNextStepKey}',
    )
    ..writeln(
      '  session: progress=${p.registrationSessionProgressPercent} '
      'step_key=${p.registrationSessionCurrentStepKey} '
      'screen=${p.registrationSessionCurrentScreenKey}',
    );

  if (!show) {
    buf.writeln(_explainWhyHidden(p));
  }

  debugPrint(buf.toString());
}

String _explainWhyHidden(MobileAppProfile p) {
  final status = (p.clientStatus ?? '').trim().toUpperCase();
  if (status == 'ACTIVE') {
    final td = p.registrationDerivedTotalCount;
    final dc = p.registrationDerivedCompletedCount;
    final macro = (p.registrationMacroStage ?? '').trim().toLowerCase();
    final r = p.registrationCompletionRatio;
    final dp = p.registrationDerivedProgressPercent;
    final missing = p.registrationMissingSteps;
    final next = p.registrationDerivedNextStepKey;
    final parts = <String>[
      'client ACTIVE',
      'dc<td=${td != null && td > 0 && dc != null && dc < td}',
      'missing=${missing?.isNotEmpty == true}',
      'nextKey=${next != null && next.trim().isNotEmpty}',
      'macro≠active=${macro.isNotEmpty && macro != "active_client"}',
      'ratio<1=${r != null && r < 0.999}',
      'dp<100=${dp != null && dp < 100}',
    ];
    return '  ⟲ masqué car ACTIVE et aucune condition de reprise: ${parts.join(" | ")}';
  }
  if (status == 'PARTIAL') {
    return '  ⟲ incohérence: PARTIAL devrait donner shouldShow=true — vérifier getter.';
  }
  return '  ⟲ masqué: pas PARTIAL, pas jalons incomplets, macro active_client ou vide, '
      'ratio 1 ou absent, dp 100 ou absent.';
}

/// Après chargement API registration (Home).
void debugLogRegistrationModuleApi({
  required String tag,
  required bool skipped,
  String? skipReason,
  String? jurisdictionCode,
  String? flowId,
  int? flowStepsCount,
  bool? canLaunch,
  Object? error,
}) {
  if (!kDebugMode) return;
  final buf = StringBuffer()..writeln('[Registration] ═══ $tag');
  if (skipped) {
    buf.writeln('  module API: SKIPPED ${skipReason ?? ""}');
    debugPrint(buf.toString());
    return;
  }
  if (error != null) {
    buf.writeln('  module API: ERREUR $error');
    debugPrint(buf.toString());
    return;
  }
  buf.writeln(
    '  module API: OK jurisdiction=$jurisdictionCode flow_id=$flowId '
    'steps=$flowStepsCount canLaunch=$canLaunch',
  );
  debugPrint(buf.toString());
}
