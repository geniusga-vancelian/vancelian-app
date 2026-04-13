import 'dart:async';

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../design_system/atoms/app_colors.dart';
import '../../../design_system/components/app_country_picker.dart';
import '../../../design_system/components/app_text_input.dart';
import '../data/registration_api.dart';
import '../data/registration_models.dart';

Map<String, String> _defaultBindingSlugs() => {
      'street': 'address_line_1',
      'postal': 'postal_code',
      'city': 'city',
      'country': 'country_of_residence',
    };

Map<String, String> _bindingSlugsFromProps(Map<String, dynamic> props) {
  final raw = props['binding_slugs'];
  final out = _defaultBindingSlugs();
  if (raw is Map) {
    for (final k in ['street', 'postal', 'city', 'country']) {
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

/// True when Places [details] `country` equals [expectedIso2Upper] (defense in depth vs backend).
bool detailsCountryMatchesExpectedResidence(
  String expectedIso2Upper,
  Map<String, dynamic> details,
) {
  final u = expectedIso2Upper.trim().toUpperCase();
  if (u.length != 2) return true;
  final got = parseIso2CountryCode(details['country']);
  return got == u;
}

/// Upper-case ISO 3166-1 alpha-2 or null if [raw] is missing / invalid.
String? parseIso2CountryCode(dynamic raw) {
  if (raw == null) return null;
  final s = raw.toString().trim();
  if (s.length != 2) return null;
  final u = s.toUpperCase();
  final a = u.codeUnitAt(0);
  final b = u.codeUnitAt(1);
  if (a < 65 || a > 90 || b < 65 || b > 90) return null;
  return u;
}

/// ISO2 codes from props_json.allowed_countries (same shape as AppCountryPicker).
List<String> allowedIso2CodesFromProps(Map<String, dynamic> props) {
  final raw = props['allowed_countries'];
  if (raw is! List || raw.isEmpty) return const [];
  final out = <String>{};
  for (final e in raw) {
    if (e is String && e.trim().length == 2) {
      out.add(e.trim().toUpperCase());
    } else if (e is Map) {
      final iso = e['iso2']?.toString().trim() ?? '';
      if (iso.length == 2) out.add(iso.toUpperCase());
    }
  }
  final list = out.toList()..sort();
  return list.length > 25 ? list.sublist(0, 25) : list;
}

/// Allowlist pour `/api/address/autocomplete` et `/details` : union du step et du pays de résidence.
/// Si le step n’a pas d’`allowed_countries`, retourne `null` (pas de paramètre `allowed_countries`).
List<String>? allowedCountriesForPlacesQuery({
  required List<String> allowedFromStep,
  String? residenceIso2,
}) {
  final res = residenceIso2?.trim().toUpperCase();
  if (allowedFromStep.isEmpty) return null;
  final merged = <String>{
    for (final c in allowedFromStep)
      if (c.trim().length == 2) c.trim().toUpperCase(),
    if (res != null && res.length == 2) res,
  };
  if (merged.isEmpty) return null;
  final out = merged.toList()..sort();
  return out.length > 25 ? out.sublist(0, 25) : out;
}

/// Smart address search (Google Places proxy) + champs éditables alignés registration slugs.
class AddressAutocompleteField extends StatefulWidget {
  const AddressAutocompleteField({
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
  });

  final RegistrationComponent comp;
  final Map<String, dynamic> formData;
  final Map<String, TextEditingController> controllers;
  final Map<String, FocusNode> focusNodes;
  final ValueChanged<MapEntry<String, dynamic>> onFieldChanged;
  final void Function(Map<String, dynamic> patch) onFormPatch;
  final RegistrationApi registrationApi;
  final Map<String, String> errors;
  /// Biais autocomplete (ex. pays déjà choisi ailleurs sur l’écran).
  final String? regionHintIso2;

  @override
  State<AddressAutocompleteField> createState() =>
      _AddressAutocompleteFieldState();
}

class _AddressAutocompleteFieldState extends State<AddressAutocompleteField> {
  late final TextEditingController _searchController;
  Timer? _debounce;
  List<Map<String, String>> _predictions = [];
  bool _loading = false;
  bool _manualOnly = false;
  final Map<String, String> _sources = {};
  bool _override = false;
  String? _uxHint;

  Map<String, String> get _sl => _bindingSlugsFromProps(widget.comp.props);

  void _showSnack(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }

  @override
  void initState() {
    super.initState();
    _searchController = TextEditingController();
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _searchController.dispose();
    super.dispose();
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

  void _onSearchChanged(String q) {
    _debounce?.cancel();
    if (_manualOnly) return;
    if (q.trim().length < 2) {
      setState(() => _predictions = []);
      return;
    }
    _debounce = Timer(const Duration(milliseconds: 300), () => _fetchPredictions(q));
  }

  Future<void> _fetchPredictions(String q) async {
    setState(() {
      _loading = true;
      _uxHint = null;
    });
    final slugBindings = _bindingSlugsFromProps(widget.comp.props);
    final residence =
        parseIso2CountryCode(widget.formData[slugBindings['country']!]);
    final allowed = allowedIso2CodesFromProps(widget.comp.props);
    final merged = allowedCountriesForPlacesQuery(
      allowedFromStep: allowed,
      residenceIso2: residence,
    );
    final r = await widget.registrationApi.addressAutocomplete(
      q,
      region: allowed.length == 1
          ? allowed.first
          : widget.regionHintIso2 ?? residence,
      allowedCountriesIso2: merged,
      countryIso2: residence,
    );
    if (!mounted) return;
    setState(() {
      _loading = false;
      if (r.isRateLimited) {
        _predictions = [];
        final wait = r.retryAfterSeconds;
        _showSnack(wait != null && wait > 0
            ? 'Too many address searches. Please wait ~${wait}s.'
            : 'Too many address searches. Please wait a moment.');
        return;
      }
      if (r.isSuccess && r.data != null) {
        final raw = r.data!['predictions'];
        if (raw is List) {
          _predictions = raw
              .whereType<Map>()
              .map((e) => Map<String, String>.from(
                    e.map((k, v) => MapEntry('$k', '$v')),
                  ))
              .where((m) =>
                  (m['description'] ?? '').isNotEmpty &&
                  (m['place_id'] ?? '').isNotEmpty)
              .toList();
          if (_predictions.isEmpty && q.trim().length >= 2) {
            _uxHint =
                'No matches — try another wording or use “My address is not listed”.';
          }
        } else {
          _predictions = [];
        }
      } else {
        _predictions = [];
        if (r.errorMessage != null && r.errorMessage!.isNotEmpty) {
          _showSnack(r.errorMessage!);
        }
      }
    });
  }

  Future<void> _selectPrediction(String placeId) async {
    setState(() {
      _loading = true;
      _predictions = [];
      _uxHint = null;
    });
    final slugBindings = _bindingSlugsFromProps(widget.comp.props);
    final residence =
        parseIso2CountryCode(widget.formData[slugBindings['country']!]);
    final allowed = allowedIso2CodesFromProps(widget.comp.props);
    final merged = allowedCountriesForPlacesQuery(
      allowedFromStep: allowed,
      residenceIso2: residence,
    );
    final r = await widget.registrationApi.addressDetails(
      placeId,
      allowedCountriesIso2: merged,
      countryIso2: residence,
    );
    if (!mounted) return;
    setState(() => _loading = false);
    if (r.isRateLimited) {
      final wait = r.retryAfterSeconds;
      _showSnack(wait != null && wait > 0
          ? 'Too many requests. Please wait ~${wait}s.'
          : 'Too many requests. Please wait a moment.');
      return;
    }
    if (r.isValidationError &&
        r.errorCode == 'address_country_mismatch') {
      _showSnack(
        'This address is outside the allowed countries. Pick another result or enter manually.',
      );
      return;
    }
    if (!r.isSuccess || r.data == null) {
      if (r.errorMessage != null && r.errorMessage!.isNotEmpty) {
        _showSnack(r.errorMessage!);
      }
      return;
    }

    final d = r.data!;
    final street = '${d['address_line_1'] ?? ''}'.trim();
    final postal = '${d['postal_code'] ?? ''}'.trim();
    final city = '${d['city'] ?? ''}'.trim();
    final country = '${d['country'] ?? ''}'.trim().toUpperCase();

    final sl = _sl;
    _setSlugValue(sl['street']!, street, 'google_places');
    _setSlugValue(sl['postal']!, postal, 'google_places');
    _setSlugValue(sl['city']!, city, 'google_places');
    _setSlugValue(sl['country']!, country, 'google_places');

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
    _override = false;
    _patchSources();
    _searchController.clear();

    final warnings = d['field_warnings'];
    if (warnings is List && warnings.isNotEmpty) {
      setState(() {
        _uxHint =
            'Some address fields could not be filled automatically — please check postal code and city.';
      });
    }
  }

  void _enableManualOnly() {
    setState(() {
      _manualOnly = true;
      _predictions = [];
      _uxHint = null;
    });
    for (final slug in _sl.values) {
      _sources[slug] = 'manual';
    }
    final metaSlug = _metadataSlug(widget.comp.props);
    if (metaSlug != null) {
      _sources[metaSlug] = 'manual';
      widget.onFieldChanged(MapEntry(metaSlug, <String, dynamic>{
        'source': 'manual',
      }));
    }
    _override = true;
    _patchSources();
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

  void _onCountryChanged(String slug, String v) {
    widget.onFieldChanged(MapEntry(slug, v));
    final prev = _sources[slug];
    if (prev == 'google_places') {
      _sources[slug] = 'hybrid';
    } else {
      _sources[slug] = 'manual';
    }
    _override = true;
    _patchSources();
  }

  @override
  Widget build(BuildContext context) {
    final p = widget.comp.props;
    final bs = _sl;
    final streetSlug = bs['street']!;
    final postalSlug = bs['postal']!;
    final citySlug = bs['city']!;
    final countrySlug = bs['country']!;

    final searchLabel = (p['search_label'] is String && (p['search_label'] as String).isNotEmpty)
        ? p['search_label'] as String
        : 'Search address';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (!_manualOnly) ...[
          Text(
            searchLabel,
            style: GoogleFonts.inter(
              fontSize: 13,
              fontWeight: FontWeight.w600,
              color: AppColors.textPrimary,
            ),
          ),
          const SizedBox(height: 6),
          TextField(
            controller: _searchController,
            onChanged: _onSearchChanged,
            decoration: InputDecoration(
              hintText: 'Start typing your address…',
              filled: true,
              fillColor: Colors.white,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
                borderSide: BorderSide(color: AppColors.textSecondary.withValues(alpha: 0.2)),
              ),
              suffixIcon: _loading
                  ? const Padding(
                      padding: EdgeInsets.all(12),
                      child: SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      ),
                    )
                  : null,
            ),
          ),
          if (_predictions.isNotEmpty)
            Container(
              margin: const EdgeInsets.only(top: 4),
              constraints: const BoxConstraints(maxHeight: 200),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppColors.textSecondary.withValues(alpha: 0.15)),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.06),
                    blurRadius: 12,
                    offset: const Offset(0, 4),
                  ),
                ],
              ),
              child: ListView.builder(
                shrinkWrap: true,
                itemCount: _predictions.length,
                itemBuilder: (ctx, i) {
                  final pr = _predictions[i];
                  return ListTile(
                    dense: true,
                    title: Text(
                      pr['description'] ?? '',
                      style: GoogleFonts.inter(fontSize: 14),
                    ),
                    onTap: () => _selectPrediction(pr['place_id'] ?? ''),
                  );
                },
              ),
            ),
          if (_uxHint != null) ...[
            const SizedBox(height: 6),
            Text(
              _uxHint!,
              style: GoogleFonts.inter(
                fontSize: 12,
                color: AppColors.textSecondary,
              ),
            ),
          ],
          TextButton(
            onPressed: _enableManualOnly,
            child: Text(
              'My address is not listed',
              style: GoogleFonts.inter(
                fontSize: 14,
                fontWeight: FontWeight.w600,
                color: AppColors.indigo,
              ),
            ),
          ),
          const SizedBox(height: 8),
        ],
        AppTextInput(
          label: '${_lineLabel(p, 'street', 'Address line 1')} *',
          controller: widget.controllers[streetSlug],
          focusNode: widget.focusNodes[streetSlug],
          onChanged: (v) => _onTextEdited(streetSlug, v),
          error: widget.errors[streetSlug],
        ),
        const SizedBox(height: 12),
        AppTextInput(
          label: '${_lineLabel(p, 'postal', 'Postal code')} *',
          controller: widget.controllers[postalSlug],
          focusNode: widget.focusNodes[postalSlug],
          onChanged: (v) => _onTextEdited(postalSlug, v),
          error: widget.errors[postalSlug],
        ),
        const SizedBox(height: 12),
        AppTextInput(
          label: '${_lineLabel(p, 'city', 'City')} *',
          controller: widget.controllers[citySlug],
          focusNode: widget.focusNodes[citySlug],
          onChanged: (v) => _onTextEdited(citySlug, v),
          error: widget.errors[citySlug],
        ),
        const SizedBox(height: 12),
        AppCountryPicker(
          label: '${_lineLabel(p, 'country', 'Country of residence')} *',
          value: widget.formData[countrySlug] as String?,
          allowedCountries: _allowedCountryPickerOptions(context, p),
          onChanged: (v) => _onCountryChanged(countrySlug, v ?? ''),
          required: true,
          error: widget.errors[countrySlug],
        ),
      ],
    );
  }

  String _lineLabel(Map<String, dynamic> p, String key, String fallback) {
    final m = p['${key}_label_i18n'];
    if (m is Map) {
      final lang = Localizations.localeOf(context).languageCode;
      for (final code in [lang, 'en', 'fr']) {
        final t = m[code];
        if (t is String && t.trim().isNotEmpty) return t.trim();
      }
    }
    final flat = p['${key}_label'];
    if (flat is String && flat.isNotEmpty) return flat;
    return fallback;
  }

  List<Map<String, String>>? _allowedCountryPickerOptions(
      BuildContext context, Map<String, dynamic> props) {
    final raw = props['allowed_countries'];
    if (raw is! List || raw.isEmpty) return null;
    final lang = Localizations.localeOf(context).languageCode;
    final useFr = lang.startsWith('fr');
    final out = <Map<String, String>>[];
    for (final e in raw) {
      if (e is! Map) continue;
      final m = Map<String, dynamic>.from(e);
      final iso = m['iso2']?.toString() ?? '';
      if (iso.isEmpty) continue;
      final en = m['label_en']?.toString() ?? iso;
      final fr = m['label_fr']?.toString() ?? en;
      out.add({'value': iso, 'label': useFr ? fr : en});
    }
    return out.isEmpty ? null : out;
  }
}
