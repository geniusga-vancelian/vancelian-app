import '../../activation/domain/activation_journey_models.dart';
import '../domain/security_preferences_models.dart';

/// Réponse `GET /api/mobile/flutter/profile` (projection person.profile_json).
class MobileAppProfile {
  const MobileAppProfile({
    required this.initials,
    required this.email,
    this.securityPreferences,
    this.personal,
    this.address,
    this.identity,
    this.contact,
    this.employment,
    this.financial,
    this.legal,
    this.jurisdiction,
    this.kycStatus,
    this.clientStatus,
    this.referenceCurrency,
    this.registrationCompletionRatio,
    this.registrationMacroStage,
    this.registrationMacroLabel,
    this.registrationMissingSteps,
    this.registrationCompletedSteps,
    this.registrationSessionProgressPercent,
    this.registrationSessionCurrentStepKey,
    this.registrationSessionCurrentScreenKey,
    this.registrationDerivedCompletionRatio,
    this.registrationDerivedProgressPercent,
    this.registrationDerivedNextStepKey,
    this.registrationDerivedNextStepLabel,
    this.registrationDerivedResumeDescription,
    this.registrationDerivedCompletedCount,
    this.registrationDerivedTotalCount,
    this.activationJourney,
  });

  final String initials;
  final String email;
  final MobileSecurityPreferences? securityPreferences;
  final MobileProfilePersonal? personal;
  final MobileProfileAddress? address;
  final MobileProfileIdentity? identity;
  final MobileProfileContact? contact;
  final MobileProfileEmployment? employment;
  final MobileProfileFinancial? financial;
  final MobileProfileLegal? legal;
  final String? jurisdiction;
  final String? kycStatus;
  final String? clientStatus;
  final String? referenceCurrency;

  /// 0..1 — même source que l’admin (`compute_canonical_registration_progress`).
  final double? registrationCompletionRatio;
  final String? registrationMacroStage;
  final String? registrationMacroLabel;
  final List<String>? registrationMissingSteps;
  final List<String>? registrationCompletedSteps;
  final int? registrationSessionProgressPercent;
  final String? registrationSessionCurrentStepKey;
  final String? registrationSessionCurrentScreenKey;

  /// Jalons depuis ``profile_json.collected`` uniquement (12 étapes canoniques).
  final double? registrationDerivedCompletionRatio;
  final int? registrationDerivedProgressPercent;
  final String? registrationDerivedNextStepKey;
  final String? registrationDerivedNextStepLabel;
  final String? registrationDerivedResumeDescription;
  final int? registrationDerivedCompletedCount;
  final int? registrationDerivedTotalCount;

  /// Parcours d’activation 3 étapes (API récente). Null si backend sans clé.
  final ActivationJourney? activationJourney;

  /// Afficher le bloc Home (activation ou, à défaut, reprise inscription legacy).
  bool get shouldShowActivationJourney {
    final j = activationJourney;
    if (j != null) {
      return j.showModule;
    }
    return shouldShowRegistrationResume;
  }

  /// True si l’inscription n’est pas considérée comme terminée côté backend.
  ///
  /// Ne pas se limiter à `PARTIAL` + ratio : en pratique, `client_status` ou le ratio
  /// peuvent être absents du JSON alors que `registration_missing_steps`, la macro
  /// ou les jalons dérivés indiquent encore un parcours incomplet.
  bool get shouldShowRegistrationResume {
    final status = (clientStatus ?? '').trim().toUpperCase();
    if (status == 'ACTIVE') {
      // En base, « ACTIVE » peut être posé avant la fin du parcours UX (KYC, profil…).
      // On réaffiche le module si un signal d’incomplétude subsiste (comme pour PARTIAL).
      final td = registrationDerivedTotalCount;
      final dc = registrationDerivedCompletedCount;
      if (td != null && td > 0 && dc != null && dc < td) return true;
      final missing = registrationMissingSteps;
      if (missing != null && missing.isNotEmpty) return true;
      final nextKey = registrationDerivedNextStepKey;
      if (nextKey != null && nextKey.trim().isNotEmpty) return true;
      final macro = (registrationMacroStage ?? '').trim().toLowerCase();
      if (macro.isNotEmpty && macro != 'active_client') return true;
      final r = registrationCompletionRatio;
      if (r != null && r < 0.999) return true;
      final dp = registrationDerivedProgressPercent;
      if (dp != null && dp < 100) return true;
      return false;
    }

    final td = registrationDerivedTotalCount;
    final dc = registrationDerivedCompletedCount;
    if (td != null && td > 0 && dc != null && dc < td) return true;

    if (status == 'PARTIAL') return true;

    if (registrationMissingSteps != null && registrationMissingSteps!.isNotEmpty) {
      return true;
    }

    final nextKey = registrationDerivedNextStepKey;
    if (nextKey != null && nextKey.trim().isNotEmpty) return true;

    final macro = (registrationMacroStage ?? '').trim();
    final macroNorm = macro.toLowerCase();
    // API : valeurs snake_case (ex. `active_client`), pas `ACTIVE_CLIENT`.
    if (macroNorm.isNotEmpty && macroNorm != 'active_client') {
      return true;
    }

    final r = registrationCompletionRatio;
    if (r != null && r < 0.999) return true;

    final dp = registrationDerivedProgressPercent;
    if (dp != null && dp < 100) return true;

    return false;
  }

  /// E-mail à montrer à l’utilisateur (profil collecté en priorité, puis champ compte).
  String? get displayEmailOrNull {
    final c = contact?.email?.trim();
    if (c != null && c.isNotEmpty) return c;
    final e = email.trim();
    if (e.isNotEmpty) return e;
    return null;
  }

  /// Barre Home : **dérivé collected** en priorité (robuste), repli ratio admin.
  int get registrationProgressDisplayPercent {
    final derived = registrationDerivedProgressPercent;
    if (derived != null) {
      return derived.clamp(0, 100);
    }
    final r = registrationCompletionRatio;
    if (r == null) return 0;
    return (r * 100).round().clamp(0, 100);
  }

  String get registrationResumeDescriptionDisplay {
    final d = registrationDerivedResumeDescription;
    if (d != null && d.isNotEmpty) return d;
    final m = registrationMacroLabel;
    if (m != null && m.isNotEmpty) return m;
    return 'Quelques informations complémentaires permettent de finaliser votre compte.';
  }

  /// Jalons restants (dérivés), si total et complétés connus.
  int? get registrationDerivedRemainingStepsCount {
    final t = registrationDerivedTotalCount;
    final d = registrationDerivedCompletedCount;
    if (t == null || d == null) return null;
    final r = t - d;
    return r < 0 ? 0 : r;
  }

  /// Ligne type « Plus que X étapes… » — levier conversion.
  String? get registrationRemainingStepsLineFr {
    final r = registrationDerivedRemainingStepsCount;
    if (r == null || r <= 0) return null;
    if (r == 1) {
      return 'Plus qu’une étape pour débloquer toutes les fonctionnalités.';
    }
    return 'Plus que $r étapes pour débloquer toutes les fonctionnalités.';
  }

  /// Accroche orientée bénéfice (Home / modal).
  static const String conversionBenefitHeadline =
      'Accédez à l’épargne, aux placements et à votre carte en quelques minutes.';

  /// Texte court pour la modal « Reprendre votre inscription ? ».
  String get registrationResumePromptModalDescription {
    final parts = <String>[];
    final pct = registrationProgressDisplayPercent;
    if (pct > 0) parts.add('$pct % complété');
    final next = registrationDerivedNextStepLabel;
    if (next != null && next.isNotEmpty) {
      parts.add('Étape suivante : $next');
    }
    final rem = registrationRemainingStepsLineFr;
    if (rem != null) parts.add(rem);
    if (parts.isEmpty) {
      return 'Quelques informations suffisent pour activer votre compte.';
    }
    return parts.join(' — ');
  }

  factory MobileAppProfile.fromJson(Map<String, dynamic> json) {
    double? ratio;
    final rawR = json['registration_completion_ratio'];
    if (rawR is num) {
      ratio = rawR.toDouble().clamp(0.0, 1.0);
    }
    int? sessPct;
    final rawP = json['registration_session_progress_percent'];
    if (rawP is int) {
      sessPct = rawP;
    } else if (rawP is num) {
      sessPct = rawP.round();
    }
    double? derivedRatio;
    final rawDr = json['registration_derived_completion_ratio'];
    if (rawDr is num) {
      derivedRatio = rawDr.toDouble().clamp(0.0, 1.0);
    }
    int? derivedPct;
    final rawDp = json['registration_derived_progress_percent'];
    if (rawDp is int) {
      derivedPct = rawDp;
    } else if (rawDp is num) {
      derivedPct = rawDp.round();
    }
    int? derivedDone;
    final rawDd = json['registration_derived_completed_count'];
    if (rawDd is int) {
      derivedDone = rawDd;
    } else if (rawDd is num) {
      derivedDone = rawDd.round();
    }
    int? derivedTotal;
    final rawDt = json['registration_derived_total_count'];
    if (rawDt is int) {
      derivedTotal = rawDt;
    } else if (rawDt is num) {
      derivedTotal = rawDt.round();
    }
    return MobileAppProfile(
      initials: (json['initials'] ?? '').toString(),
      email: (json['email'] ?? '').toString(),
      securityPreferences: _securityPreferencesFromJson(json['security_preferences']),
      personal: _section(json['personal'], MobileProfilePersonal.fromJson),
      address: _section(json['address'], MobileProfileAddress.fromJson),
      identity: _section(json['identity'], MobileProfileIdentity.fromJson),
      contact: _section(json['contact'], MobileProfileContact.fromJson),
      employment: _section(json['employment'], MobileProfileEmployment.fromJson),
      financial: _section(json['financial'], MobileProfileFinancial.fromJson),
      legal: _section(json['legal'], MobileProfileLegal.fromJson),
      jurisdiction: _s(json['jurisdiction']),
      kycStatus: _s(json['kyc_status']),
      clientStatus: _s(json['client_status']),
      referenceCurrency: _s(json['reference_currency']),
      registrationCompletionRatio: ratio,
      registrationMacroStage: _s(json['registration_macro_stage']),
      registrationMacroLabel: _s(json['registration_macro_label']),
      registrationMissingSteps: _stringList(json['registration_missing_steps']),
      registrationCompletedSteps: _stringList(json['registration_completed_steps']),
      registrationSessionProgressPercent: sessPct,
      registrationSessionCurrentStepKey:
          _s(json['registration_session_current_step_key']),
      registrationSessionCurrentScreenKey:
          _s(json['registration_session_current_screen_key']),
      registrationDerivedCompletionRatio: derivedRatio,
      registrationDerivedProgressPercent: derivedPct,
      registrationDerivedNextStepKey: _s(json['registration_derived_next_step_key']),
      registrationDerivedNextStepLabel:
          _s(json['registration_derived_next_step_label']),
      registrationDerivedResumeDescription:
          _s(json['registration_derived_resume_description']),
      registrationDerivedCompletedCount: derivedDone,
      registrationDerivedTotalCount: derivedTotal,
      activationJourney: _activationJourneyFromJson(json['activation_journey']),
    );
  }

  static MobileSecurityPreferences? _securityPreferencesFromJson(Object? raw) {
    if (raw is! Map<String, dynamic>) return null;
    return MobileSecurityPreferences.fromJson(raw);
  }

  static ActivationJourney? _activationJourneyFromJson(Object? raw) {
    if (raw is! Map<String, dynamic>) return null;
    try {
      return ActivationJourney.fromJson(raw);
    } catch (_) {
      return null;
    }
  }

  static List<String>? _stringList(Object? raw) {
    if (raw is! List) return null;
    return raw.map((e) => e.toString()).where((s) => s.isNotEmpty).toList();
  }

  static T? _section<T>(
    Object? raw,
    T Function(Map<String, dynamic>) from,
  ) {
    if (raw is! Map<String, dynamic>) return null;
    if (raw.isEmpty) return null;
    return from(raw);
  }
}

class MobileProfilePersonal {
  const MobileProfilePersonal({
    this.firstName,
    this.lastName,
    this.dateOfBirth,
    this.nationality,
  });

  final String? firstName;
  final String? lastName;
  final String? dateOfBirth;
  final String? nationality;

  factory MobileProfilePersonal.fromJson(Map<String, dynamic> json) {
    return MobileProfilePersonal(
      firstName: _s(json['first_name']),
      lastName: _s(json['last_name']),
      dateOfBirth: _s(json['date_of_birth']),
      nationality: _s(json['nationality']),
    );
  }
}

class MobileProfileAddress {
  const MobileProfileAddress({
    this.line1,
    this.line2,
    this.postalCode,
    this.city,
    this.country,
  });

  final String? line1;
  final String? line2;
  final String? postalCode;
  final String? city;
  final String? country;

  factory MobileProfileAddress.fromJson(Map<String, dynamic> json) {
    return MobileProfileAddress(
      line1: _s(json['line1']),
      line2: _s(json['line2']),
      postalCode: _s(json['postal_code']),
      city: _s(json['city']),
      country: _s(json['country']),
    );
  }
}

class MobileProfileIdentity {
  const MobileProfileIdentity({
    this.documentType,
    this.documentNumberMasked,
    this.documentExpiry,
  });

  final String? documentType;
  final String? documentNumberMasked;
  final String? documentExpiry;

  factory MobileProfileIdentity.fromJson(Map<String, dynamic> json) {
    return MobileProfileIdentity(
      documentType: _s(json['document_type']),
      documentNumberMasked: _s(json['document_number_masked']),
      documentExpiry: _s(json['document_expiry']),
    );
  }
}

class MobileProfileContact {
  const MobileProfileContact({this.email, this.phone});

  final String? email;
  final String? phone;

  factory MobileProfileContact.fromJson(Map<String, dynamic> json) {
    return MobileProfileContact(
      email: _s(json['email']),
      phone: _s(json['phone']),
    );
  }
}

class MobileProfileEmployment {
  const MobileProfileEmployment({
    this.employmentStatus,
    this.jobTitle,
    this.workSector,
    this.employerName,
  });

  final String? employmentStatus;
  final String? jobTitle;
  final String? workSector;
  final String? employerName;

  factory MobileProfileEmployment.fromJson(Map<String, dynamic> json) {
    return MobileProfileEmployment(
      employmentStatus: _s(json['employment_status']),
      jobTitle: _s(json['job_title']),
      workSector: _s(json['work_sector']),
      employerName: _s(json['employer_name']),
    );
  }
}

class MobileProfileFinancial {
  const MobileProfileFinancial({
    this.annualIncomeRange,
    this.netWorthRange,
    this.sourceOfWealth,
  });

  final String? annualIncomeRange;
  final String? netWorthRange;
  final String? sourceOfWealth;

  factory MobileProfileFinancial.fromJson(Map<String, dynamic> json) {
    return MobileProfileFinancial(
      annualIncomeRange: _s(json['annual_income_range']),
      netWorthRange: _s(json['net_worth_range']),
      sourceOfWealth: _s(json['source_of_wealth']),
    );
  }
}

class MobileProfileLegal {
  const MobileProfileLegal({
    this.termsAccepted,
    this.infoTrueAndAccurate,
    this.complianceUsageAck,
    this.notUsPerson,
  });

  final String? termsAccepted;
  final String? infoTrueAndAccurate;
  final String? complianceUsageAck;
  final String? notUsPerson;

  factory MobileProfileLegal.fromJson(Map<String, dynamic> json) {
    return MobileProfileLegal(
      termsAccepted: _s(json['terms_accepted']),
      infoTrueAndAccurate: _s(json['info_true_and_accurate']),
      complianceUsageAck: _s(json['compliance_usage_ack']),
      notUsPerson: _s(json['not_us_person']),
    );
  }
}

String? _s(Object? v) {
  if (v == null) return null;
  final t = v.toString().trim();
  return t.isEmpty ? null : t;
}

