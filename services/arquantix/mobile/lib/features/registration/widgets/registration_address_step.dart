import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../design_system/atoms/app_colors.dart';
import '../../../design_system/atoms/app_spacing.dart';
import '../../../design_system/components/app_text_input.dart';
import '../data/registration_api.dart';
import '../data/registration_models.dart';
import 'address_autocomplete_field.dart';
import 'address_search_modal.dart';

/// Patche le [_formData] du flow pour [RegistrationFlowScreen._allRequiredFilled].
const kRegAddressStepSurfaceKey = '__reg_address_step_surface__';

/// Pays manquant ou non reconnaissable comme ISO2 autorisé → pas de recherche ni champs ligne.
const kRegAddressSurfaceNeedCountry = 'need_country';

/// Pays valide, recherche visible, lignes d’adresse encore masquées.
const kRegAddressSurfaceSearchOnly = 'search_only';

/// Lignes d’adresse affichées (saisie manuelle ou après suggestion) ou mode sans recherche.
const kRegAddressSurfaceEditing = 'editing';

const _defaultBindings = {
  'postal_code': 'postal_code',
  'address_line_1': 'address_line_1',
  'address_line_2': 'address_line_2',
  'city': 'city',
  'country_of_residence': 'country_of_residence',
};

Map<String, String> _bindingsFromProps(Map<String, dynamic> props) {
  final raw = props['binding_slugs'];
  final out = Map<String, String>.from(_defaultBindings);
  if (raw is Map) {
    for (final k in _defaultBindings.keys) {
      final v = raw[k];
      if (v is String && v.trim().isNotEmpty) {
        out[k] = v.trim();
      }
    }
  }
  return out;
}

String? _metadataSlug(Map<String, dynamic> props) {
  final m = props['metadata_slug'];
  if (m is String && m.trim().isNotEmpty) return m.trim();
  if (props['store_place_id'] == true) return 'address_metadata';
  return null;
}

String _localizedString(
  BuildContext context,
  dynamic raw,
  String fallback,
) {
  if (raw is String && raw.trim().isNotEmpty) return raw.trim();
  if (raw is Map) {
    final lang = Localizations.localeOf(context).languageCode;
    for (final code in [lang, 'en', 'fr']) {
      final t = raw[code];
      if (t is String && t.trim().isNotEmpty) return t.trim();
    }
  }
  return fallback;
}

/// Priorité : `*_i18n` (locale) → clés legacy string (`title`, …) → [fallback].
String _resolveAddressStepString(
  BuildContext context,
  Map<String, dynamic> p, {
  required String i18nKey,
  required String legacyKey,
  required String fallback,
}) {
  final i18n = p[i18nKey];
  if (i18n is Map) {
    final s = _localizedString(context, i18n, '');
    if (s.isNotEmpty) return s;
  }
  final leg = p[legacyKey];
  if (leg is String && leg.trim().isNotEmpty) return leg.trim();
  return fallback;
}

String _fieldLabel(
  BuildContext context,
  Map<String, dynamic> p,
  String fieldKey,
  String fallbackBase,
  bool required,
) {
  final m = p['field_labels_i18n'];
  var base = fallbackBase.replaceAll(RegExp(r'\s*\*$'), '').trim();
  if (m is Map && m[fieldKey] != null) {
    final r = _localizedString(context, m[fieldKey], '');
    if (r.isNotEmpty) {
      base = r.replaceAll(RegExp(r'\s*\*$'), '').trim();
    }
  }
  if (required) {
    return base.endsWith('*') ? base : '$base *';
  }
  return base;
}

String? _fieldPlaceholder(
  BuildContext context,
  Map<String, dynamic> p,
  String fieldKey,
) {
  final m = p['field_placeholders_i18n'];
  if (m is! Map || m[fieldKey] == null) return null;
  final s = _localizedString(context, m[fieldKey], '');
  return s.isEmpty ? null : s;
}

int _intProp(Map<String, dynamic> p, String key, int defaultValue) {
  final v = p[key];
  if (v is int) return v;
  if (v is num) return v.toInt();
  return defaultValue;
}

bool _boolProp(Map<String, dynamic> p, String key, bool defaultValue) {
  final v = p[key];
  if (v is bool) return v;
  return defaultValue;
}

void _addressStepLog(String message) {
  if (kDebugMode) {
    debugPrint('[RegistrationAddressStep] $message');
  }
}

/// Panneau d’adresse pour le registration flow (`component_type`: `address_step`).
///
/// Le **pays de résidence** doit être saisi en amont (écran séparé, ex. `country_picker`) :
/// [formData] contient déjà l’ISO2 sous le slug [binding_slugs.country_of_residence].
/// Recherche Places (si `search_enabled`) dès que ce pays est valide / autorisé ;
/// champs ligne uniquement après suggestion ou « pas trouvé ».
/// Patche [kRegAddressStepSurfaceKey] pour la validation du CTA côté écran.
/// Composant métier autonome : trigger + bottom sheet recherche (style Revolut),
/// appels [RegistrationApi], sync [controllers] / [formData] via [onFieldChanged] /
/// [onFormPatch] (`__reg_address_sources__`, override), sans exposer [metadata_slug].
///
/// Les [controllers] / [focusNodes] restent fournis par l’écran parent pour survivre
/// aux reconstructions du flow.
///
/// Si [embedTitleAndSubtitle] est `false`, le titre / sous-titre du widget ne sont pas
/// rendus (l’écran parent affiche déjà le même contenu via `screen.title` / `subtitle`).
class RegistrationAddressStep extends StatefulWidget {
  const RegistrationAddressStep({
    super.key,
    required this.comp,
    required this.formData,
    required this.controllers,
    required this.focusNodes,
    required this.onFieldChanged,
    required this.onFormPatch,
    required this.registrationApi,
    required this.errors,
    this.regionHintIso2,
    this.embedTitleAndSubtitle = true,
  });

  final RegistrationComponent comp;
  final Map<String, dynamic> formData;
  final Map<String, TextEditingController> controllers;
  final Map<String, FocusNode> focusNodes;
  final ValueChanged<MapEntry<String, dynamic>> onFieldChanged;
  final void Function(Map<String, dynamic> patch) onFormPatch;
  final RegistrationApi registrationApi;
  final Map<String, String> errors;
  final String? regionHintIso2;

  /// `false` dans le flux standard quand [RegistrationFlowScreen] affiche déjà titre + sous-titre.
  final bool embedTitleAndSubtitle;

  @override
  State<RegistrationAddressStep> createState() => _RegistrationAddressStepState();
}

class _RegistrationAddressStepState extends State<RegistrationAddressStep> {
  /// Résumé affiché dans le trigger après choix Places (optionnel).
  String? _addressSearchTriggerSummary;
  /// [addressDetails] en cours après fermeture de la modale.
  bool _resolvingPlaceDetails = false;
  /// Lignes d’adresse (rue, CP, ville, ligne 2) visibles après suggestion ou « pas trouvé ».
  bool _addressFieldsVisible = false;
  final Map<String, String> _sources = {};
  bool _override = false;

  Map<String, String> get _sl => _bindingsFromProps(widget.comp.props);

  bool get _searchEnabled =>
      _boolProp(widget.comp.props, 'search_enabled', true);

  int get _minChars => _intProp(widget.comp.props, 'search_min_chars', 2)
      .clamp(1, 20);

  int get _debounceMs => _intProp(widget.comp.props, 'search_debounce_ms', 300)
      .clamp(50, 5000);

  bool get _line2Optional =>
      _boolProp(widget.comp.props, 'address_line_2_optional', true);

  /// ISO2 dérivé du slug pays (indépendamment de `allowed_countries`).
  String? get _parsedResidenceIso2 {
    final slug = _sl['country_of_residence']!;
    return parseIso2CountryCode(widget.formData[slug]);
  }

  List<String> get _allowedIso2ForStep =>
      allowedIso2CodesFromProps(widget.comp.props);

  /// Recherche : dès qu’un ISO2 résidence valide est présent (source de vérité = écran amont).
  bool get _showSearchSection =>
      _searchEnabled && _parsedResidenceIso2 != null;

  String _addressSearchDisallowedMessage(BuildContext context) {
    final fr = Localizations.localeOf(context).languageCode.startsWith('fr');
    return fr
        ? 'La recherche d’adresse n’est pas disponible pour ce pays'
        : 'Address search is not available for this country';
  }

  String _detailsCountryMismatchMessage(BuildContext context) {
    final fr =
        Localizations.localeOf(context).languageCode.startsWith('fr');
    return fr
        ? 'L’adresse sélectionnée ne correspond pas à votre pays de résidence. '
            'Saisissez l’adresse manuellement ou choisissez un autre résultat.'
        : 'The selected address does not match your country of residence. '
            'Enter the address manually or pick another result.';
  }

  String _missingSessionCountryMessage(BuildContext context) {
    final fr = Localizations.localeOf(context).languageCode.startsWith('fr');
    return fr
        ? 'Le pays de résidence doit être renseigné à l’étape précédente. '
            'Revenez en arrière ou contactez le support.'
        : 'Country of residence should be set on the previous step. '
            'Go back or contact support.';
  }

  void _showSnack(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        behavior: SnackBarBehavior.floating,
        margin: const EdgeInsets.all(AppSpacing.md),
      ),
    );
  }

  @override
  void initState() {
    super.initState();
    _addressFieldsVisible = _computeInitialAddressFieldsVisible();
    // Ne pas appeler _syncSurface() ici : onFormPatch → setState parent pendant le build
    // de [RegistrationFlowRenderer] provoque "setState() called during build".
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _syncSurface();
    });
  }

  bool _computeInitialAddressFieldsVisible() {
    if (_parsedResidenceIso2 == null) return false;
    if (!_searchEnabled) return true;
    final bs = _sl;
    for (final k in ['address_line_1', 'postal_code', 'city']) {
      final v = widget.formData[bs[k]!];
      if (v is String && v.trim().isNotEmpty) return true;
    }
    return false;
  }

  void _syncSurface() {
    if (!mounted) return;
    final String surface;
    if (_parsedResidenceIso2 == null) {
      surface = kRegAddressSurfaceNeedCountry;
    } else if (!_searchEnabled) {
      surface = kRegAddressSurfaceEditing;
    } else if (!_addressFieldsVisible) {
      surface = kRegAddressSurfaceSearchOnly;
    } else {
      surface = kRegAddressSurfaceEditing;
    }
    widget.onFormPatch({kRegAddressStepSurfaceKey: surface});
  }

  void _clearAddressLinesOnly() {
    final bs = _sl;
    for (final key in ['address_line_1', 'address_line_2', 'postal_code', 'city']) {
      final slug = bs[key]!;
      final c = widget.controllers[slug];
      if (c != null) c.text = '';
      widget.onFieldChanged(MapEntry(slug, ''));
      _sources[slug] = 'manual';
    }
    final metaSlug = _metadataSlug(widget.comp.props);
    if (metaSlug != null) {
      widget.onFieldChanged(MapEntry(metaSlug, <String, dynamic>{}));
      _sources[metaSlug] = 'manual';
    }
  }

  void _resetForCountryChange() {
    if (!mounted) return;
    setState(() {
      _addressSearchTriggerSummary = null;
      _addressFieldsVisible = !_searchEnabled && _parsedResidenceIso2 != null;
    });
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      _syncSurface();
      _clearAddressLinesOnly();
      _override = false;
      _patchSources();
      _syncSurface();
    });
  }

  @override
  void didUpdateWidget(covariant RegistrationAddressStep oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.formData[kRegAddressStepSurfaceKey] != null &&
        widget.formData[kRegAddressStepSurfaceKey] == null) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _syncSurface();
      });
    }
    final slug = _sl['country_of_residence']!;
    final oldIso = parseIso2CountryCode(oldWidget.formData[slug]);
    final newIso = parseIso2CountryCode(widget.formData[slug]);
    if (oldIso != newIso) {
      _resetForCountryChange();
    }
    if (oldWidget.comp.id != widget.comp.id) {
      if (!mounted) return;
      setState(() {
        _addressSearchTriggerSummary = null;
        _addressFieldsVisible = _computeInitialAddressFieldsVisible();
      });
      _syncSurface();
    } else if (oldIso == newIso) {
      final reveal = _computeInitialAddressFieldsVisible();
      if (reveal && !_addressFieldsVisible) {
        setState(() => _addressFieldsVisible = true);
        _syncSurface();
      }
    }
  }

  @override
  void dispose() {
    super.dispose();
  }

  String _searchTriggerDisplayText(String searchLabel) {
    // Adresse saisie / préremplie dans les champs : la barre reste sur le libellé seul.
    if (_addressFieldsVisible) return '';
    final s = _addressSearchTriggerSummary?.trim();
    if (s != null && s.isNotEmpty) return s;
    return '';
  }

  Future<void> _openAddressSearchModal() async {
    if (!_showSearchSection) return;
    final p = widget.comp.props;
    final searchLabel = _resolveAddressStepString(
      context,
      p,
      i18nKey: 'search_label_i18n',
      legacyKey: 'search_label',
      fallback: 'Rechercher une adresse',
    );
    final manualLabel = _resolveAddressStepString(
      context,
      p,
      i18nKey: 'manual_entry_label_i18n',
      legacyKey: 'manual_entry_label',
      fallback: "Mon adresse n'est pas ici",
    );
    final residence = _parsedResidenceIso2!;
    final result = await showAddressSearchModal(
      context: context,
      snackBarMessenger: ScaffoldMessenger.maybeOf(context),
      registrationApi: widget.registrationApi,
      minChars: _minChars,
      debounceMs: _debounceMs,
      residenceIso2: residence,
      allowedIso2: _allowedIso2ForStep,
      regionHintIso2: widget.regionHintIso2,
      searchLabel: searchLabel,
      manualLabel: manualLabel,
    );
    if (!mounted) return;
    if (result is AddressSearchModalPlaceId) {
      final desc = result.description?.trim();
      setState(() {
        _addressSearchTriggerSummary =
            (desc != null && desc.isNotEmpty) ? desc : null;
      });
      await _selectPrediction(result.placeId);
    } else if (result is AddressSearchModalManual) {
      _revealManualAddressFields();
    }
  }

  void _patchSources() {
    widget.onFormPatch({
      '__reg_address_sources__': Map<String, String>.from(_sources),
      if (_override) '__reg_address_override__': true,
    });
  }

  void _setSlugValue(String slug, String value, String source) {
    final c = widget.controllers[slug];
    if (c != null) {
      c.text = value;
    }
    widget.onFieldChanged(MapEntry(slug, value));
    _sources[slug] = source;
    _patchSources();
  }

  Future<void> _selectPrediction(String placeId) async {
    if (_parsedResidenceIso2 == null) {
      _addressStepLog('selectPrediction ignored: residence ISO2 missing');
      if (mounted) {
        _showSnack(_addressSearchDisallowedMessage(context));
      }
      return;
    }
    _addressStepLog('API addressDetails place_id=$placeId');
    setState(() => _resolvingPlaceDetails = true);
    final residence = _parsedResidenceIso2;
    final detailsAllowed = allowedCountriesForPlacesQuery(
      allowedFromStep: _allowedIso2ForStep,
      residenceIso2: residence,
    );
    try {
      final r = await widget.registrationApi.addressDetails(
        placeId,
        allowedCountriesIso2: detailsAllowed,
        countryIso2: residence,
      );
      if (!mounted) return;

      void failClearSummary() {
        if (mounted) setState(() => _addressSearchTriggerSummary = null);
      }

      if (r.isRateLimited) {
        failClearSummary();
        final wait = r.retryAfterSeconds;
        _showSnack(wait != null && wait > 0
            ? 'Trop de requêtes. Réessayez dans ~${wait}s.'
            : 'Trop de requêtes. Patientez un instant.');
        return;
      }
      if (r.isValidationError && r.errorCode == 'address_country_mismatch') {
        failClearSummary();
        _showSnack(
          'Cette adresse est hors zone autorisée. Choisissez un autre résultat ou saisissez manuellement.',
        );
        return;
      }
      if (r.isValidationError && r.errorCode == 'country_not_in_allowed_list') {
        failClearSummary();
        _showSnack(_addressSearchDisallowedMessage(context));
        return;
      }
      if (!r.isSuccess || r.data == null) {
        failClearSummary();
        _showSnack(
          (r.errorMessage != null && r.errorMessage!.trim().isNotEmpty)
              ? r.errorMessage!.trim()
              : 'Impossible de récupérer cette adresse. Réessayez ou saisissez manuellement.',
        );
        return;
      }

      final d = Map<String, dynamic>.from(r.data!);
      if (residence != null &&
          !detailsCountryMatchesExpectedResidence(residence, d)) {
        failClearSummary();
        _showSnack(_detailsCountryMismatchMessage(context));
        return;
      }

      final street = '${d['address_line_1'] ?? ''}'.trim();
      final postal = '${d['postal_code'] ?? ''}'.trim();
      final city = '${d['city'] ?? ''}'.trim();
      final apiCountry = '${d['country'] ?? ''}'.trim().toUpperCase();

      final bs = _sl;
      _setSlugValue(bs['address_line_1']!, street, 'google_places');
      _setSlugValue(bs['postal_code']!, postal, 'google_places');
      _setSlugValue(bs['city']!, city, 'google_places');
      // Toujours aligner sur le pays de session (étape amont), pas sur le libellé Google seul.
      final countrySlug = bs['country_of_residence']!;
      final sessionIso = residence?.toUpperCase();
      final resolvedCountry = (sessionIso != null && sessionIso.isNotEmpty)
          ? sessionIso
          : apiCountry;
      _setSlugValue(countrySlug, resolvedCountry, 'google_places');
      _setSlugValue(bs['address_line_2']!, '', 'google_places');

      final metaSlug = _metadataSlug(widget.comp.props);
      if (metaSlug != null) {
        final meta = <String, dynamic>{
          'place_id': d['google_place_id'] ?? placeId,
          'confidence_score': d['confidence_score'],
          'source': 'google_places',
          'formatted_address': d['formatted_address'],
          'lat': d['lat'],
          'lng': d['lng'],
        };
        widget.onFieldChanged(MapEntry(metaSlug, meta));
        _sources[metaSlug] = 'google_places';
      }
      _addressStepLog(
        'autofill applied line1="$street" postal="$postal" city="$city" '
        'country=$resolvedCountry meta=${metaSlug != null}',
      );
      _override = false;
      _patchSources();

      final warnings = d['field_warnings'];
      if (warnings is List && warnings.isNotEmpty) {
        _showSnack(
          'Certains champs n’ont pas été remplis automatiquement — vérifiez le code postal et la ville.',
        );
      }
      setState(() {
        _addressFieldsVisible = true;
        _addressSearchTriggerSummary = null;
      });
      _syncSurface();
    } finally {
      if (mounted) setState(() => _resolvingPlaceDetails = false);
    }
  }

  void _revealManualAddressFields() {
    _addressStepLog('revealManualAddressFields');
    _clearAddressLinesOnly();
    setState(() {
      _addressSearchTriggerSummary = null;
      _addressFieldsVisible = true;
    });
    _override = true;
    _patchSources();
    _syncSurface();
  }

  void _onTextEdited(String slug, String v) {
    widget.onFieldChanged(MapEntry(slug, v));
    final prev = _sources[slug];
    if (prev == 'google_places') {
      _sources[slug] = 'hybrid';
    } else if (prev == null || prev == 'manual') {
      _sources[slug] = 'manual';
    }
    _override = true;
    _patchSources();
  }

  Widget _buildTitleBlock(BuildContext context, Map<String, dynamic> p) {
    final title = _resolveAddressStepString(
      context,
      p,
      i18nKey: 'title_i18n',
      legacyKey: 'title',
      fallback: '',
    );
    final subtitle = _resolveAddressStepString(
      context,
      p,
      i18nKey: 'subtitle_i18n',
      legacyKey: 'subtitle',
      fallback: '',
    );
    if (title.isEmpty) return const SizedBox.shrink();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          title,
          style: GoogleFonts.inter(
            fontSize: 26,
            fontWeight: FontWeight.w700,
            letterSpacing: -0.6,
            height: 1.15,
            color: AppColors.textPrimary,
          ),
        ),
        if (subtitle.isNotEmpty) ...[
          const SizedBox(height: AppSpacing.sm + 2),
          Text(
            subtitle,
            style: GoogleFonts.inter(
              fontSize: 15,
              fontWeight: FontWeight.w400,
              height: 22 / 15,
              color: AppColors.textSecondary,
            ),
          ),
        ],
        const SizedBox(height: AppSpacing.lg + 4),
      ],
    );
  }

  /// Pays absent de la session (flow mal ordonné) ou données corrompues.
  Widget _buildMissingSessionCountryBanner(BuildContext context) {
    if (_parsedResidenceIso2 != null) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.lg),
      child: DecoratedBox(
        decoration: BoxDecoration(
          color: AppColors.semanticWarningLight,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: AppColors.semanticWarning.withValues(alpha: 0.35),
          ),
        ),
        child: Padding(
          padding: const EdgeInsets.all(AppSpacing.md),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(
                Icons.info_outline_rounded,
                size: 20,
                color: AppColors.semanticWarning.withValues(alpha: 0.95),
              ),
              const SizedBox(width: AppSpacing.sm),
              Expanded(
                child: Text(
                  _missingSessionCountryMessage(context),
                  style: GoogleFonts.inter(
                    fontSize: 13,
                    height: 1.35,
                    color: AppColors.textPrimary,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildSearchSection(Map<String, dynamic> p) {
    if (!_showSearchSection) return const SizedBox.shrink();

    final searchLabel = _resolveAddressStepString(
      context,
      p,
      i18nKey: 'search_label_i18n',
      legacyKey: 'search_label',
      fallback: 'Rechercher une adresse',
    );
    // Gabarit [AppTextInput] : hauteur 56, rayon 16, fond blanc (champ classique).
    const triggerRadius = 16.0;
    const triggerHeight = 56.0;
    const iconColor = Color(0xFF8E8E93);
    final display = _searchTriggerDisplayText(searchLabel);
    final hasDisplay = display.isNotEmpty;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Semantics(
          button: true,
          label: searchLabel,
          enabled: !_resolvingPlaceDetails,
          excludeSemantics: true,
          child: Material(
            color: Colors.white,
            borderRadius: BorderRadius.circular(triggerRadius),
            clipBehavior: Clip.antiAlias,
            child: InkWell(
              key: const ValueKey<String>('registration_address_search_trigger'),
              onTap: _resolvingPlaceDetails ? null : _openAddressSearchModal,
              borderRadius: BorderRadius.circular(triggerRadius),
              child: SizedBox(
                height: triggerHeight,
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.center,
                    children: [
                      const Icon(
                        Icons.search_rounded,
                        color: iconColor,
                        size: 22,
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          hasDisplay ? display : searchLabel,
                          style: GoogleFonts.inter(
                            fontSize: 17,
                            fontWeight: FontWeight.w600,
                            height: 22 / 17,
                            letterSpacing: -0.43,
                            color: hasDisplay ? Colors.black : iconColor,
                          ),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      if (_resolvingPlaceDetails)
                        const Padding(
                          padding: EdgeInsets.only(left: AppSpacing.sm),
                          child: SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(
                              strokeWidth: 2,
                              color: AppColors.indigo,
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
        const SizedBox(height: AppSpacing.lg),
      ],
    );
  }

  /// Champs ligne d’adresse (rue, complément, CP, ville — pas de pays à l’écran).
  Widget _buildAddressFields(BuildContext context, Map<String, dynamic> p) {
    if (!_addressFieldsVisible) return const SizedBox.shrink();

    final bs = _sl;
    final postalSlug = bs['postal_code']!;
    final line1Slug = bs['address_line_1']!;
    final line2Slug = bs['address_line_2']!;
    final citySlug = bs['city']!;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        AppTextInput(
          label: _fieldLabel(
            context,
            p,
            'address_line_1',
            'Rue, numéro',
            true,
          ),
          description: _fieldPlaceholder(context, p, 'address_line_1'),
          controller: widget.controllers[line1Slug],
          focusNode: widget.focusNodes[line1Slug],
          onChanged: (v) => _onTextEdited(line1Slug, v),
          error: widget.errors[line1Slug],
        ),
        const SizedBox(height: AppSpacing.md),
        AppTextInput(
          label: _fieldLabel(
            context,
            p,
            'address_line_2',
            _line2Optional
                ? 'Étage, appartement (optionnel)'
                : 'Étage, appartement',
            !_line2Optional,
          ),
          description: _fieldPlaceholder(context, p, 'address_line_2'),
          controller: widget.controllers[line2Slug],
          focusNode: widget.focusNodes[line2Slug],
          onChanged: (v) => _onTextEdited(line2Slug, v),
          error: widget.errors[line2Slug],
        ),
        const SizedBox(height: AppSpacing.md),
        AppTextInput(
          label: _fieldLabel(
            context,
            p,
            'postal_code',
            'Code postal',
            true,
          ),
          description: _fieldPlaceholder(context, p, 'postal_code'),
          controller: widget.controllers[postalSlug],
          focusNode: widget.focusNodes[postalSlug],
          onChanged: (v) => _onTextEdited(postalSlug, v),
          error: widget.errors[postalSlug],
        ),
        const SizedBox(height: AppSpacing.md),
        AppTextInput(
          label: _fieldLabel(
            context,
            p,
            'city',
            'Ville',
            true,
          ),
          description: _fieldPlaceholder(context, p, 'city'),
          controller: widget.controllers[citySlug],
          focusNode: widget.focusNodes[citySlug],
          onChanged: (v) => _onTextEdited(citySlug, v),
          error: widget.errors[citySlug],
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    final p = widget.comp.props;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (widget.embedTitleAndSubtitle) _buildTitleBlock(context, p),
        _buildMissingSessionCountryBanner(context),
        _buildSearchSection(p),
        _buildAddressFields(context, p),
      ],
    );
  }
}
