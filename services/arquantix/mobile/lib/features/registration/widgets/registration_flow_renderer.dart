import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../design_system/atoms/app_colors.dart';
import '../../../design_system/components/app_checkbox.dart';
import '../../../design_system/components/app_country_picker.dart';
import '../../../design_system/components/app_date_input.dart';
import '../../../core/ui/selectable_multi_list.dart';
import '../../../core/ui/selectable_single_list.dart';
import '../../../design_system/components/app_phone_input.dart';
import '../../../design_system/components/app_text_input.dart';
import '../data/registration_api.dart';
import '../data/registration_models.dart';
import 'address_autocomplete_field.dart';
import 'registration_address_step.dart';

String _labelForOption(List<Map<String, String>> options, String value) {
  for (final o in options) {
    if (o['value'] == value) return o['label'] ?? value;
  }
  return value;
}

/// Slugs déjà gérés par un composant `address_step` / `address_autocomplete` sur l’écran.
/// Évite les doublons (ex. `text_input` sur `address_metadata`) et le champ technique visible.
Set<String> addressCompositeConsumedBindingSlugs(
    List<RegistrationComponent> components) {
  final out = <String>{};
  for (final c in components) {
    if (c.componentType == 'address_step') {
      final raw = c.props['binding_slugs'];
      const def = {
        'postal_code': 'postal_code',
        'address_line_1': 'address_line_1',
        'address_line_2': 'address_line_2',
        'city': 'city',
        'country_of_residence': 'country_of_residence',
      };
      if (raw is Map) {
        for (final k in def.keys) {
          final v = raw[k];
          out.add(v is String && v.isNotEmpty ? v : def[k]!);
        }
      } else {
        out.addAll(def.values);
      }
      final ms = c.props['metadata_slug'];
      if (ms is String && ms.trim().isNotEmpty) {
        out.add(ms.trim());
      }
      if (c.props['store_place_id'] == true) {
        out.add('address_metadata');
      }
    } else if (c.componentType == 'address_autocomplete') {
      final raw = c.props['binding_slugs'];
      const def = {
        'street': 'address_line_1',
        'postal': 'postal_code',
        'city': 'city',
        'country': 'country_of_residence',
      };
      if (raw is Map) {
        for (final k in def.keys) {
          final v = raw[k];
          out.add(v is String && v.isNotEmpty ? v : def[k]!);
        }
      } else {
        out.addAll(def.values);
      }
      final ms = c.props['metadata_slug'];
      if (ms is String && ms.trim().isNotEmpty) {
        out.add(ms.trim());
      }
      if (c.props['store_place_id'] == true) {
        out.add('address_metadata');
      }
    }
  }
  return out;
}

bool _isDuplicateOfAddressComposite(
  RegistrationComponent c,
  Set<String> consumedSlugs,
) {
  if (c.componentType == 'address_step' ||
      c.componentType == 'address_autocomplete') {
    return false;
  }
  final slug = c.bindingSlug;
  if (slug == null || slug.isEmpty) return false;
  if (!consumedSlugs.contains(slug)) return false;
  const skippable = {
    'text_input',
    'country_picker',
    'select',
    'multi_select',
    'date_picker',
  };
  return skippable.contains(c.componentType);
}

String? _countryIsoFromAddressProps(
  Map<String, dynamic> formData,
  Map<String, dynamic> props,
) {
  final bs = props['binding_slugs'];
  var countryKey = 'country_of_residence';
  if (bs is Map) {
    if (bs['country_of_residence'] is String &&
        (bs['country_of_residence'] as String).isNotEmpty) {
      countryKey = bs['country_of_residence'] as String;
    } else if (bs['country'] is String &&
        (bs['country'] as String).isNotEmpty) {
      countryKey = bs['country'] as String;
    }
  }
  final v = formData[countryKey];
  if (v is String && v.length == 2) return v.toUpperCase();
  return null;
}

/// Renders a list of dynamic form components from the Registration Flow API.
///
/// Maps each [RegistrationComponent.componentType] to the appropriate DS
/// widget and wires form data read/write through [onFieldChanged].
///
/// Text controllers are managed externally via [controllers] to survive
/// rebuilds without losing user input.
class RegistrationFlowRenderer extends StatelessWidget {
  const RegistrationFlowRenderer({
    super.key,
    required this.components,
    required this.formData,
    required this.controllers,
    required this.onFieldChanged,
    this.onPhoneNationalChanged,
    this.focusNodes = const {},
    this.errors = const {},
    this.registrationApi,
    this.onFormPatch,
    /// Quand l’écran affiche déjà [RegistrationFlowScreen] titre + sous-titre,
    /// masquer le bloc titre du `address_step` pour éviter la duplication.
    this.screenProvidesPageHeading = false,
  });

  final List<RegistrationComponent> components;
  final Map<String, dynamic> formData;

  /// Controllers for text-based fields, keyed by binding_slug.
  final Map<String, TextEditingController> controllers;

  /// FocusNodes for text-based fields, keyed by binding_slug.
  final Map<String, FocusNode> focusNodes;

  final ValueChanged<MapEntry<String, dynamic>> onFieldChanged;

  /// When set, national phone input updates both ``slug`` and ``{slug}_raw`` for backend submit.
  final void Function(String slug, String nationalInput)? onPhoneNationalChanged;

  /// Field-level validation errors keyed by binding_slug.
  final Map<String, String> errors;

  final RegistrationApi? registrationApi;

  /// Fusionne des clés dans le formulaire (ex. `__reg_address_sources__`).
  final void Function(Map<String, dynamic> patch)? onFormPatch;

  final bool screenProvidesPageHeading;

  static const _textComponentTypes = {'text_input', 'phone_input'};

  @override
  Widget build(BuildContext context) {
    final consumedByAddress = addressCompositeConsumedBindingSlugs(components);
    final textSlugs = <String>[];
    for (final c in components) {
      if (_textComponentTypes.contains(c.componentType)) {
        final s = c.bindingSlug;
        if (s != null) textSlugs.add(s);
      } else if (c.componentType == 'address_autocomplete') {
        final bs = c.props['binding_slugs'];
        final def = {
          'street': 'address_line_1',
          'postal': 'postal_code',
          'city': 'city',
        };
        if (bs is Map) {
          for (final k in ['street', 'postal', 'city']) {
            final v = bs[k];
            if (v is String && v.isNotEmpty) {
              textSlugs.add(v);
            } else if (def[k] != null) {
              textSlugs.add(def[k]!);
            }
          }
        } else {
          textSlugs.addAll(def.values);
        }
      } else if (c.componentType == 'address_step') {
        final bs = c.props['binding_slugs'];
        const keys = [
          'postal_code',
          'address_line_1',
          'address_line_2',
          'city',
        ];
        const def = {
          'postal_code': 'postal_code',
          'address_line_1': 'address_line_1',
          'address_line_2': 'address_line_2',
          'city': 'city',
        };
        if (bs is Map) {
          for (final k in keys) {
            final v = bs[k];
            if (v is String && v.isNotEmpty) {
              textSlugs.add(v);
            } else {
              textSlugs.add(def[k]!);
            }
          }
        } else {
          textSlugs.addAll(def.values);
        }
      }
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: components
          .map((c) => _buildComponent(
                context,
                c,
                textSlugs,
                consumedByAddress,
                screenProvidesPageHeading,
              ))
          .toList(),
    );
  }

  Widget _buildComponent(
    BuildContext context,
    RegistrationComponent comp,
    List<String> textSlugs,
    Set<String> consumedByAddress,
    bool screenProvidesPageHeading,
  ) {
    if (_isDuplicateOfAddressComposite(comp, consumedByAddress)) {
      return const SizedBox.shrink();
    }
    final slug = comp.bindingSlug;
    final fieldError = slug != null ? errors[slug] : null;
    final isLastText = slug != null && textSlugs.isNotEmpty && slug == textSlugs.last;
    final textAction = isLastText ? TextInputAction.done : TextInputAction.next;

    switch (comp.componentType) {
      case 'address_autocomplete':
        final api = registrationApi;
        final patch = onFormPatch;
        if (api == null || patch == null) {
          return Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: Text(
              'Address search requires registrationApi + onFormPatch',
              style: GoogleFonts.inter(fontSize: 13, color: AppColors.errorText),
            ),
          );
        }
        return Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: AddressAutocompleteField(
            comp: comp,
            formData: formData,
            controllers: controllers,
            focusNodes: focusNodes,
            onFieldChanged: onFieldChanged,
            onFormPatch: patch,
            registrationApi: api,
            errors: errors,
            regionHintIso2: _countryIsoFromAddressProps(formData, comp.props),
          ),
        );

      // Composant métier : recherche modale + champs ligne ; pays lu depuis formData (écran amont).
      case 'address_step':
        final apiStep = registrationApi;
        final patchStep = onFormPatch;
        if (apiStep == null || patchStep == null) {
          return Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: Text(
              'Address step requires registrationApi + onFormPatch',
              style: GoogleFonts.inter(fontSize: 13, color: AppColors.errorText),
            ),
          );
        }
        return Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: RegistrationAddressStep(
            comp: comp,
            formData: formData,
            controllers: controllers,
            focusNodes: focusNodes,
            onFieldChanged: onFieldChanged,
            onFormPatch: patchStep,
            registrationApi: apiStep,
            errors: errors,
            regionHintIso2: _countryIsoFromAddressProps(formData, comp.props),
            embedTitleAndSubtitle: !screenProvidesPageHeading,
          ),
        );

      case 'text_input':
        return Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: AppTextInput(
            label: comp.isRequired ? '${comp.label} *' : comp.label,
            controller: slug != null ? controllers[slug] : null,
            focusNode: slug != null ? focusNodes[slug] : null,
            textInputAction: textAction,
            onChanged: slug != null
                ? (v) => onFieldChanged(MapEntry(slug, v))
                : null,
            error: fieldError,
            keyboardType: _keyboardTypeFor(comp.props),
          ),
        );

      case 'phone_input':
        final countrySlug = slug != null ? '${slug}_country_code' : null;
        final currentCountry =
            countrySlug != null ? formData[countrySlug] as String? : null;
        final p = comp.props;
        return Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: AppPhoneInput(
            label: comp.isRequired ? '${comp.label} *' : comp.label,
            countryCode: currentCountry,
            phoneController: slug != null ? controllers[slug] : null,
            phoneFocusNode: slug != null ? focusNodes[slug] : null,
            textInputAction: textAction,
            allowedPhoneCountries: _allowedPhoneCountriesFromProps(p),
            defaultPhoneCountryIso2: _defaultPhoneCountryFromProps(p),
            onCountryChanged: countrySlug != null
                ? (v) => onFieldChanged(MapEntry(countrySlug, v))
                : null,
            onPhoneChanged: slug == null
                ? null
                : (onPhoneNationalChanged != null
                    ? (v) => onPhoneNationalChanged!(slug, v)
                    : (v) => onFieldChanged(MapEntry(slug, v))),
            error: fieldError,
            showInlineError: false,
          ),
        );

      case 'checkbox':
        final rawDesc = comp.props['description'];
        final description = rawDesc is String
            ? rawDesc
            : rawDesc is Map
                ? (rawDesc['en'] ?? rawDesc.values.firstOrNull)?.toString()
                : null;
        final isChecked = formData[slug] == true;
        return Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: Container(
            width: double.infinity,
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(16),
            ),
            child: AppCheckbox(
              label: comp.label,
              description: description,
              checked: isChecked,
              onChanged: slug != null
                  ? (v) => onFieldChanged(MapEntry(slug, v))
                  : null,
            ),
          ),
        );

      case 'section_title':
        return Padding(
          padding: const EdgeInsets.only(top: 8, bottom: 12),
          child: Text(
            comp.label,
            style: GoogleFonts.inter(
              fontSize: 20,
              fontWeight: FontWeight.w700,
              letterSpacing: -0.45,
              height: 25 / 20,
            ),
          ),
        );

      case 'legal_content':
        final text =
            comp.props['text'] as String? ??
            comp.props['content'] as String? ??
            '';
        return Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: Container(
            width: double.infinity,
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: const Color(0xFFF5F5F5),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Text(
              text,
              style: GoogleFonts.inter(
                fontSize: 13,
                fontWeight: FontWeight.w400,
                height: 18 / 13,
                color: AppColors.textSecondary,
              ),
            ),
          ),
        );

      case 'info_box':
        final text =
            comp.props['text'] as String? ??
            comp.props['content'] as String? ??
            '';
        return Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: Container(
            width: double.infinity,
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: AppColors.semanticInfoLight,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: AppColors.semanticInfo.withValues(alpha: 0.3),
              ),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Icon(Icons.info_outline_rounded,
                    size: 18, color: AppColors.semanticInfo),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    text,
                    style: GoogleFonts.inter(
                      fontSize: 13,
                      fontWeight: FontWeight.w400,
                      height: 18 / 13,
                      color: AppColors.textPrimary,
                    ),
                  ),
                ),
              ],
            ),
          ),
        );

      case 'select':
        final options = _parseOptions(comp.props['options']);
        final valueKeys = options
            .map((e) => e['value'] ?? '')
            .where((v) => v.isNotEmpty)
            .toList();
        if (slug == null || valueKeys.isEmpty) {
          return const SizedBox.shrink();
        }
        return Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (comp.label.isNotEmpty && !comp.hideInlineLabel)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Text(
                    comp.isRequired ? '${comp.label} *' : comp.label,
                    style: GoogleFonts.inter(
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                      height: 18 / 14,
                    ),
                  ),
                ),
              SelectableSingleList<String>(
                items: valueKeys,
                selected: formData[slug] as String?,
                onSelect: (v) => onFieldChanged(MapEntry(slug, v)),
                labelBuilder: (v) => _labelForOption(options, v),
                encapsulateInCard: true,
              ),
              if (fieldError != null && fieldError.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: Text(
                    fieldError,
                    style: GoogleFonts.inter(
                      fontSize: 13,
                      fontWeight: FontWeight.w400,
                      height: 16 / 13,
                      letterSpacing: -0.08,
                      color: const Color(0xFFFF2D55),
                    ),
                  ),
                ),
            ],
          ),
        );

      case 'country_picker':
        final countryVal = (formData[slug] as String?) ??
            (comp.props['default_country'] as String?);
        return Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: AppCountryPicker(
            label: comp.label,
            value: countryVal,
            allowedCountries:
                _allowedCountryPickerOptions(context, comp.props),
            onChanged: slug != null
                ? (v) => onFieldChanged(MapEntry(slug, v))
                : (_) {},
            required: comp.isRequired,
            error: fieldError,
          ),
        );

      case 'date_picker':
        DateTime? current;
        final raw = formData[slug];
        if (raw is DateTime) {
          current = raw;
        } else if (raw is String && raw.isNotEmpty) {
          current = DateTime.tryParse(raw);
        }
        final isBirth = comp.bindingSlug?.contains('birth') == true ||
            comp.label.toLowerCase().contains('birth') ||
            comp.label.toLowerCase().contains('naissance');
        return Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: AppDateInput(
            label: comp.label,
            value: current,
            isBirthDate: isBirth,
            onChanged: slug != null
                ? (v) {
                    final formatted = v != null
                        ? '${v.year.toString().padLeft(4, '0')}-${v.month.toString().padLeft(2, '0')}-${v.day.toString().padLeft(2, '0')}'
                        : null;
                    onFieldChanged(MapEntry(slug, formatted));
                  }
                : (_) {},
            required: comp.isRequired,
            error: fieldError,
          ),
        );

      case 'multi_select':
        final options = _parseOptions(comp.props['options']);
        final valueKeys = options
            .map((e) => e['value'] ?? '')
            .where((v) => v.isNotEmpty)
            .toList();
        final currentValues = <String>[];
        final raw = formData[slug];
        if (raw is List) {
          for (final v in raw) {
            currentValues.add(v.toString());
          }
        }
        if (slug == null || valueKeys.isEmpty) {
          return const SizedBox.shrink();
        }
        final selectedSet = currentValues.toSet();
        return Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (comp.label.isNotEmpty && !comp.hideInlineLabel)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8),
                  child: Text(
                    comp.isRequired ? '${comp.label} *' : comp.label,
                    style: GoogleFonts.inter(
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                      height: 18 / 14,
                    ),
                  ),
                ),
              SelectableMultiList<String>(
                items: valueKeys,
                selectedItems: selectedSet,
                onToggle: (v) {
                  final next = List<String>.from(currentValues);
                  if (next.contains(v)) {
                    next.remove(v);
                  } else {
                    next.add(v);
                  }
                  onFieldChanged(MapEntry(slug, next));
                },
                labelBuilder: (v) => _labelForOption(options, v),
                encapsulateInCard: true,
              ),
              if (fieldError != null && fieldError.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: Text(
                    fieldError,
                    style: GoogleFonts.inter(
                      fontSize: 13,
                      fontWeight: FontWeight.w400,
                      height: 16 / 13,
                      letterSpacing: -0.08,
                      color: const Color(0xFFFF2D55),
                    ),
                  ),
                ),
            ],
          ),
        );

      case 'link_text':
        final linkLabel = comp.props['link_label'] as String? ?? '';
        final linkUrl = comp.props['link_url'] as String? ?? '';
        return Padding(
          padding: const EdgeInsets.only(bottom: 12, top: 4),
          child: _LinkTextWidget(
            text: comp.label,
            linkLabel: linkLabel,
            linkUrl: linkUrl,
          ),
        );

      case 'rich_text':
        final richText =
            comp.props['text'] as String? ??
            comp.props['content'] as String? ??
            '';
        return Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: Text(
            richText,
            style: GoogleFonts.inter(
              fontSize: 14,
              fontWeight: FontWeight.w400,
              height: 20 / 14,
              color: AppColors.textSecondary,
            ),
          ),
        );

      case 'divider':
        return Padding(
          padding: const EdgeInsets.symmetric(vertical: 8),
          child: Divider(
            height: 1,
            thickness: 1,
            color: AppColors.textSecondary.withValues(alpha: 0.15),
          ),
        );

      case 'spacer':
        final height = (comp.props['height'] as num?)?.toDouble() ?? 16;
        return SizedBox(height: height);

      case 'bullet_list':
        final items = <String>[];
        final rawItems = comp.props['items'];
        if (rawItems is List) {
          for (final item in rawItems) {
            items.add(item.toString());
          }
        }
        return Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (comp.label.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: Text(
                    comp.label,
                    style: GoogleFonts.inter(
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                      height: 18 / 14,
                    ),
                  ),
                ),
              ...items.map(
                (item) => Padding(
                  padding: const EdgeInsets.only(bottom: 4, left: 4),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('•  ',
                          style: GoogleFonts.inter(
                              fontSize: 14,
                              color: AppColors.textSecondary)),
                      Expanded(
                        child: Text(
                          item,
                          style: GoogleFonts.inter(
                            fontSize: 14,
                            fontWeight: FontWeight.w400,
                            height: 20 / 14,
                            color: AppColors.textSecondary,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        );

      default:
        return const SizedBox.shrink();
    }
  }

  /// Backend-driven allowlist for `phone_input` (`allowed_phone_countries`).
  List<Map<String, dynamic>>? _allowedPhoneCountriesFromProps(
      Map<String, dynamic> props) {
    final raw = props['allowed_phone_countries'];
    if (raw is! List || raw.isEmpty) return null;
    final out = <Map<String, dynamic>>[];
    for (final e in raw) {
      if (e is Map) out.add(Map<String, dynamic>.from(e));
    }
    return out.isEmpty ? null : out;
  }

  String? _defaultPhoneCountryFromProps(Map<String, dynamic> props) {
    final v = props['default_phone_country'];
    if (v is String && v.isNotEmpty) return v;
    return null;
  }

  /// Backend-driven options for `country_picker` (`allowed_countries`).
  /// Liste déjà filtrée par juridiction / binding (résidence vs nationalité) côté API.
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

  TextInputType? _keyboardTypeFor(Map<String, dynamic> props) {
    final inputType = props['input_type'] as String?;
    switch (inputType) {
      case 'email':
        return TextInputType.emailAddress;
      case 'number':
        return TextInputType.number;
      case 'phone':
        return TextInputType.phone;
      default:
        return null;
    }
  }

  List<Map<String, String>> _parseOptions(dynamic raw) {
    if (raw is! List) return [];
    return raw.map<Map<String, String>>((item) {
      if (item is Map) {
        return {
          'value': (item['value'] ?? '').toString(),
          'label': (item['label'] ?? item['value'] ?? '').toString(),
        };
      }
      return {'value': item.toString(), 'label': item.toString()};
    }).toList();
  }
}

/// Inline text + tappable link.
/// Example: "Already have an account? [Log in]"
class _LinkTextWidget extends StatefulWidget {
  const _LinkTextWidget({
    required this.text,
    required this.linkLabel,
    required this.linkUrl,
  });

  final String text;
  final String linkLabel;
  final String linkUrl;

  @override
  State<_LinkTextWidget> createState() => _LinkTextWidgetState();
}

class _LinkTextWidgetState extends State<_LinkTextWidget> {
  TapGestureRecognizer? _recognizer;

  @override
  void initState() {
    super.initState();
    if (widget.linkUrl.isNotEmpty) {
      _recognizer = TapGestureRecognizer()..onTap = _onLinkTap;
    }
  }

  @override
  void dispose() {
    _recognizer?.dispose();
    super.dispose();
  }

  void _onLinkTap() async {
    final uri = Uri.tryParse(widget.linkUrl);
    if (uri != null && await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }

  @override
  Widget build(BuildContext context) {
    final baseStyle = GoogleFonts.inter(
      fontSize: 14,
      fontWeight: FontWeight.w400,
      height: 20 / 14,
      letterSpacing: -0.15,
      color: AppColors.textSecondary,
    );

    final children = <InlineSpan>[];

    if (widget.text.isNotEmpty) {
      children.add(TextSpan(text: '${widget.text} '));
    }

    if (widget.linkLabel.isNotEmpty) {
      children.add(TextSpan(
        text: widget.linkLabel,
        style: const TextStyle(
          color: AppColors.indigo,
          fontWeight: FontWeight.w500,
        ),
        recognizer: _recognizer,
      ));
    }

    return Text.rich(
      TextSpan(style: baseStyle, children: children),
    );
  }
}
