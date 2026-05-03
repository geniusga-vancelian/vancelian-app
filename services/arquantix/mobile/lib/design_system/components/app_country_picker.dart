import 'package:circle_flags/circle_flags.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_spacing.dart';
import '../atoms/grabber.dart';
import '../atoms/kalai_icons.dart';
import 'app_search_input.dart';
import 'app_sheet_list_item.dart';
import 'kalai_icon.dart';
import 'sheet_title_bar.dart';

/// Sélecteur de pays (liste ISO 3166-1 + recherche dans une bottom sheet).
///
/// Stores the ISO alpha-2 code as value (e.g. "FR", "US").
class AppCountryPicker extends StatefulWidget {
  const AppCountryPicker({
    super.key,
    required this.label,
    this.value,
    required this.onChanged,
    this.required = false,
    this.enabled = true,
    this.error,
    this.allowedCountries,
  });

  final String label;
  final String? value;
  final ValueChanged<String?> onChanged;
  final bool required;
  final bool enabled;
  final String? error;

  /// When set by the registration API (`allowed_countries`), only these options
  /// appear in the sheet. Maps use `value` (ISO2) and `label` (already localized).
  final List<Map<String, String>>? allowedCountries;

  @override
  State<AppCountryPicker> createState() => _AppCountryPickerState();
}

class _AppCountryPickerState extends State<AppCountryPicker> {
  bool _isOpen = false;

  static const _containerHeight = 56.0;
  static const _radius = 16.0;
  static const _labelColor = Color(0xFF8E8E93);

  static const _errorColor = Color(0xFFFF2D55);

  bool get _hasError => widget.error != null && widget.error!.isNotEmpty;
  bool get _hasValue => widget.value != null && widget.value!.isNotEmpty;

  String? get _displayName {
    if (!_hasValue) return null;
    final code = widget.value!.toUpperCase();
    final opts = widget.allowedCountries;
    if (opts != null && opts.isNotEmpty) {
      for (final c in opts) {
        if (c['value'] == code) return c['label'];
      }
      return code;
    }
    for (final c in _countries) {
      if (c['value'] == code) return c['label'];
    }
    return code;
  }

  Color get _borderColor {
    if (_hasError) return _errorColor;
    if (_isOpen) return AppColors.indigo;
    return Colors.white;
  }

  @override
  Widget build(BuildContext context) {
    final displayLabel =
        widget.required ? '${widget.label} *' : widget.label;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        GestureDetector(
          onTap: widget.enabled ? () => _showPicker(context) : null,
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 250),
            curve: Curves.easeInOut,
            height: _containerHeight,
            decoration: BoxDecoration(
              color: widget.enabled
                  ? Colors.white
                  : const Color(0xFFF5F5F5),
              borderRadius: BorderRadius.circular(_radius),
              border: Border.all(color: _borderColor, width: 1.5),
            ),
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Row(
              children: [
                if (_hasValue) ...[
                  CircleFlag(
                    widget.value!.toLowerCase(),
                    size: 28,
                  ),
                  const SizedBox(width: 10),
                ],
                Expanded(
                  child: Stack(
                    children: [
                      if (_hasValue)
                        Positioned(
                          left: 0,
                          right: 0,
                          top: 24,
                          child: Text(
                            _displayName ?? '',
                            style: GoogleFonts.inter(
                              fontSize: 17,
                              fontWeight: FontWeight.w600,
                              height: 1.0,
                              letterSpacing: -0.43,
                              color: Colors.black,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                      Positioned(
                        left: 0,
                        top: _hasValue ? 8 : 16,
                        child: IgnorePointer(
                          child: Text(
                            displayLabel,
                            style: _hasValue
                                ? GoogleFonts.inter(
                                    fontSize: 11,
                                    fontWeight: FontWeight.w600,
                                    height: 13 / 11,
                                    letterSpacing: 0.06,
                                    color: const Color(0xFFD1D1D6),
                                  )
                                : GoogleFonts.inter(
                                    fontSize: 17,
                                    fontWeight: FontWeight.w600,
                                    height: 22 / 17,
                                    letterSpacing: -0.43,
                                    color: _labelColor,
                                  ),
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                KalaiIcon(
                  KalaiIcons.chevronDown,
                  size: 24,
                  color: widget.enabled
                      ? _labelColor
                      : const Color(0xFF808080),
                ),
              ],
            ),
          ),
        ),
        if (_hasError)
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text(
              widget.error!,
              style: GoogleFonts.inter(
                fontSize: 13,
                fontWeight: FontWeight.w400,
                height: 16 / 13,
                letterSpacing: -0.08,
                color: _errorColor,
              ),
            ),
          ),
      ],
    );
  }

  void _showPicker(BuildContext context) {
    setState(() => _isOpen = true);
    showModalBottomSheet<String>(
      context: context,
      backgroundColor: Colors.white,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (ctx) => _CountryPickerSheet(
        label: widget.label,
        selectedValue: widget.value,
        options: widget.allowedCountries,
      ),
    ).then((selected) {
      if (mounted) setState(() => _isOpen = false);
      if (selected != null) widget.onChanged(selected);
    });
  }
}

class _CountryPickerSheet extends StatefulWidget {
  const _CountryPickerSheet({
    required this.label,
    this.selectedValue,
    this.options,
  });

  final String label;
  final String? selectedValue;

  /// If non-empty, replaces the built-in world list (registration API).
  final List<Map<String, String>>? options;

  @override
  State<_CountryPickerSheet> createState() => _CountryPickerSheetState();
}

class _CountryPickerSheetState extends State<_CountryPickerSheet> {
  late final TextEditingController _searchCtrl;
  late final ScrollController _scrollCtrl;
  String _query = '';

  static const _itemExtent = 72.0;

  List<Map<String, String>> get _sourceCountries {
    final o = widget.options;
    if (o != null && o.isNotEmpty) return o;
    return _countries;
  }

  @override
  void initState() {
    super.initState();
    _searchCtrl = TextEditingController();

    final selectedIdx = _sourceCountries.indexWhere(
      (c) => c['value'] == widget.selectedValue,
    );
    final offset = selectedIdx > 2
        ? (selectedIdx - 2) * _itemExtent
        : 0.0;
    _scrollCtrl = ScrollController(initialScrollOffset: offset);
  }

  @override
  void dispose() {
    _searchCtrl.dispose();
    _scrollCtrl.dispose();
    super.dispose();
  }

  List<Map<String, String>> get _filtered {
    if (_query.isEmpty) return _sourceCountries;
    final q = _query.toLowerCase();
    return _sourceCountries.where((c) {
      return (c['label'] ?? '').toLowerCase().contains(q) ||
          (c['value'] ?? '').toLowerCase().contains(q);
    }).toList();
  }

  @override
  Widget build(BuildContext context) {
    final sheetHeight = MediaQuery.of(context).size.height * 0.9;
    return SizedBox(
      height: sheetHeight,
      child: Column(
        children: [
          const Grabber(),
          SheetTitleBar(
            title: widget.label,
            leadingButton: SheetCircleButton.leading(
              onTap: () => Navigator.pop(context),
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
            child: AppSearchInput(
              placeholder: 'Search…',
              controller: _searchCtrl,
              variant: AppSearchInputVariant.gray,
              autofocus: false,
              onChanged: (v) => setState(() => _query = v),
            ),
          ),
          const SizedBox(height: AppSpacing.sm),
          Expanded(
            child: ListView.builder(
              controller: _query.isEmpty ? _scrollCtrl : null,
              itemExtent: _itemExtent,
              keyboardDismissBehavior:
                  ScrollViewKeyboardDismissBehavior.onDrag,
              padding: EdgeInsets.only(
                left: AppSpacing.sm,
                right: AppSpacing.sm,
                bottom: MediaQuery.of(context).viewInsets.bottom,
              ),
              itemCount: _filtered.length,
              itemBuilder: (_, i) {
                final c = _filtered[i];
                final isSelected = c['value'] == widget.selectedValue;
                final code = c['value'] ?? '';
                return AppSheetListItem(
                  title: c['label'] ?? '',
                  subtitle: code,
                  leading: CircleFlag(
                    code.toLowerCase(),
                    size: 36,
                  ),
                  selected: isSelected,
                  showChevron: true,
                  onTap: () => Navigator.pop(context, code),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

const List<Map<String, String>> _countries = [
  {'value': 'AF', 'label': 'Afghanistan'},
  {'value': 'AL', 'label': 'Albania'},
  {'value': 'DZ', 'label': 'Algeria'},
  {'value': 'AD', 'label': 'Andorra'},
  {'value': 'AO', 'label': 'Angola'},
  {'value': 'AG', 'label': 'Antigua and Barbuda'},
  {'value': 'AR', 'label': 'Argentina'},
  {'value': 'AM', 'label': 'Armenia'},
  {'value': 'AU', 'label': 'Australia'},
  {'value': 'AT', 'label': 'Austria'},
  {'value': 'AZ', 'label': 'Azerbaijan'},
  {'value': 'BS', 'label': 'Bahamas'},
  {'value': 'BH', 'label': 'Bahrain'},
  {'value': 'BD', 'label': 'Bangladesh'},
  {'value': 'BB', 'label': 'Barbados'},
  {'value': 'BY', 'label': 'Belarus'},
  {'value': 'BE', 'label': 'Belgium'},
  {'value': 'BZ', 'label': 'Belize'},
  {'value': 'BJ', 'label': 'Benin'},
  {'value': 'BT', 'label': 'Bhutan'},
  {'value': 'BO', 'label': 'Bolivia'},
  {'value': 'BA', 'label': 'Bosnia and Herzegovina'},
  {'value': 'BW', 'label': 'Botswana'},
  {'value': 'BR', 'label': 'Brazil'},
  {'value': 'BN', 'label': 'Brunei'},
  {'value': 'BG', 'label': 'Bulgaria'},
  {'value': 'BF', 'label': 'Burkina Faso'},
  {'value': 'BI', 'label': 'Burundi'},
  {'value': 'CV', 'label': 'Cabo Verde'},
  {'value': 'KH', 'label': 'Cambodia'},
  {'value': 'CM', 'label': 'Cameroon'},
  {'value': 'CA', 'label': 'Canada'},
  {'value': 'CF', 'label': 'Central African Republic'},
  {'value': 'TD', 'label': 'Chad'},
  {'value': 'CL', 'label': 'Chile'},
  {'value': 'CN', 'label': 'China'},
  {'value': 'CO', 'label': 'Colombia'},
  {'value': 'KM', 'label': 'Comoros'},
  {'value': 'CG', 'label': 'Congo'},
  {'value': 'CD', 'label': 'Congo (DRC)'},
  {'value': 'CR', 'label': 'Costa Rica'},
  {'value': 'CI', 'label': "Côte d'Ivoire"},
  {'value': 'HR', 'label': 'Croatia'},
  {'value': 'CU', 'label': 'Cuba'},
  {'value': 'CY', 'label': 'Cyprus'},
  {'value': 'CZ', 'label': 'Czech Republic'},
  {'value': 'DK', 'label': 'Denmark'},
  {'value': 'DJ', 'label': 'Djibouti'},
  {'value': 'DM', 'label': 'Dominica'},
  {'value': 'DO', 'label': 'Dominican Republic'},
  {'value': 'EC', 'label': 'Ecuador'},
  {'value': 'EG', 'label': 'Egypt'},
  {'value': 'SV', 'label': 'El Salvador'},
  {'value': 'GQ', 'label': 'Equatorial Guinea'},
  {'value': 'ER', 'label': 'Eritrea'},
  {'value': 'EE', 'label': 'Estonia'},
  {'value': 'SZ', 'label': 'Eswatini'},
  {'value': 'ET', 'label': 'Ethiopia'},
  {'value': 'FJ', 'label': 'Fiji'},
  {'value': 'FI', 'label': 'Finland'},
  {'value': 'FR', 'label': 'France'},
  {'value': 'GA', 'label': 'Gabon'},
  {'value': 'GM', 'label': 'Gambia'},
  {'value': 'GE', 'label': 'Georgia'},
  {'value': 'DE', 'label': 'Germany'},
  {'value': 'GH', 'label': 'Ghana'},
  {'value': 'GR', 'label': 'Greece'},
  {'value': 'GD', 'label': 'Grenada'},
  {'value': 'GT', 'label': 'Guatemala'},
  {'value': 'GN', 'label': 'Guinea'},
  {'value': 'GW', 'label': 'Guinea-Bissau'},
  {'value': 'GY', 'label': 'Guyana'},
  {'value': 'HT', 'label': 'Haiti'},
  {'value': 'HN', 'label': 'Honduras'},
  {'value': 'HU', 'label': 'Hungary'},
  {'value': 'IS', 'label': 'Iceland'},
  {'value': 'IN', 'label': 'India'},
  {'value': 'ID', 'label': 'Indonesia'},
  {'value': 'IR', 'label': 'Iran'},
  {'value': 'IQ', 'label': 'Iraq'},
  {'value': 'IE', 'label': 'Ireland'},
  {'value': 'IL', 'label': 'Israel'},
  {'value': 'IT', 'label': 'Italy'},
  {'value': 'JM', 'label': 'Jamaica'},
  {'value': 'JP', 'label': 'Japan'},
  {'value': 'JO', 'label': 'Jordan'},
  {'value': 'KZ', 'label': 'Kazakhstan'},
  {'value': 'KE', 'label': 'Kenya'},
  {'value': 'KI', 'label': 'Kiribati'},
  {'value': 'KP', 'label': 'North Korea'},
  {'value': 'KR', 'label': 'South Korea'},
  {'value': 'KW', 'label': 'Kuwait'},
  {'value': 'KG', 'label': 'Kyrgyzstan'},
  {'value': 'LA', 'label': 'Laos'},
  {'value': 'LV', 'label': 'Latvia'},
  {'value': 'LB', 'label': 'Lebanon'},
  {'value': 'LS', 'label': 'Lesotho'},
  {'value': 'LR', 'label': 'Liberia'},
  {'value': 'LY', 'label': 'Libya'},
  {'value': 'LI', 'label': 'Liechtenstein'},
  {'value': 'LT', 'label': 'Lithuania'},
  {'value': 'LU', 'label': 'Luxembourg'},
  {'value': 'MG', 'label': 'Madagascar'},
  {'value': 'MW', 'label': 'Malawi'},
  {'value': 'MY', 'label': 'Malaysia'},
  {'value': 'MV', 'label': 'Maldives'},
  {'value': 'ML', 'label': 'Mali'},
  {'value': 'MT', 'label': 'Malta'},
  {'value': 'MH', 'label': 'Marshall Islands'},
  {'value': 'MR', 'label': 'Mauritania'},
  {'value': 'MU', 'label': 'Mauritius'},
  {'value': 'MX', 'label': 'Mexico'},
  {'value': 'FM', 'label': 'Micronesia'},
  {'value': 'MD', 'label': 'Moldova'},
  {'value': 'MC', 'label': 'Monaco'},
  {'value': 'MN', 'label': 'Mongolia'},
  {'value': 'ME', 'label': 'Montenegro'},
  {'value': 'MA', 'label': 'Morocco'},
  {'value': 'MZ', 'label': 'Mozambique'},
  {'value': 'MM', 'label': 'Myanmar'},
  {'value': 'NA', 'label': 'Namibia'},
  {'value': 'NR', 'label': 'Nauru'},
  {'value': 'NP', 'label': 'Nepal'},
  {'value': 'NL', 'label': 'Netherlands'},
  {'value': 'NZ', 'label': 'New Zealand'},
  {'value': 'NI', 'label': 'Nicaragua'},
  {'value': 'NE', 'label': 'Niger'},
  {'value': 'NG', 'label': 'Nigeria'},
  {'value': 'MK', 'label': 'North Macedonia'},
  {'value': 'NO', 'label': 'Norway'},
  {'value': 'OM', 'label': 'Oman'},
  {'value': 'PK', 'label': 'Pakistan'},
  {'value': 'PW', 'label': 'Palau'},
  {'value': 'PS', 'label': 'Palestine'},
  {'value': 'PA', 'label': 'Panama'},
  {'value': 'PG', 'label': 'Papua New Guinea'},
  {'value': 'PY', 'label': 'Paraguay'},
  {'value': 'PE', 'label': 'Peru'},
  {'value': 'PH', 'label': 'Philippines'},
  {'value': 'PL', 'label': 'Poland'},
  {'value': 'PT', 'label': 'Portugal'},
  {'value': 'QA', 'label': 'Qatar'},
  {'value': 'RO', 'label': 'Romania'},
  {'value': 'RU', 'label': 'Russia'},
  {'value': 'RW', 'label': 'Rwanda'},
  {'value': 'KN', 'label': 'Saint Kitts and Nevis'},
  {'value': 'LC', 'label': 'Saint Lucia'},
  {'value': 'VC', 'label': 'Saint Vincent and the Grenadines'},
  {'value': 'WS', 'label': 'Samoa'},
  {'value': 'SM', 'label': 'San Marino'},
  {'value': 'ST', 'label': 'São Tomé and Príncipe'},
  {'value': 'SA', 'label': 'Saudi Arabia'},
  {'value': 'SN', 'label': 'Senegal'},
  {'value': 'RS', 'label': 'Serbia'},
  {'value': 'SC', 'label': 'Seychelles'},
  {'value': 'SL', 'label': 'Sierra Leone'},
  {'value': 'SG', 'label': 'Singapore'},
  {'value': 'SK', 'label': 'Slovakia'},
  {'value': 'SI', 'label': 'Slovenia'},
  {'value': 'SB', 'label': 'Solomon Islands'},
  {'value': 'SO', 'label': 'Somalia'},
  {'value': 'ZA', 'label': 'South Africa'},
  {'value': 'SS', 'label': 'South Sudan'},
  {'value': 'ES', 'label': 'Spain'},
  {'value': 'LK', 'label': 'Sri Lanka'},
  {'value': 'SD', 'label': 'Sudan'},
  {'value': 'SR', 'label': 'Suriname'},
  {'value': 'SE', 'label': 'Sweden'},
  {'value': 'CH', 'label': 'Switzerland'},
  {'value': 'SY', 'label': 'Syria'},
  {'value': 'TW', 'label': 'Taiwan'},
  {'value': 'TJ', 'label': 'Tajikistan'},
  {'value': 'TZ', 'label': 'Tanzania'},
  {'value': 'TH', 'label': 'Thailand'},
  {'value': 'TL', 'label': 'Timor-Leste'},
  {'value': 'TG', 'label': 'Togo'},
  {'value': 'TO', 'label': 'Tonga'},
  {'value': 'TT', 'label': 'Trinidad and Tobago'},
  {'value': 'TN', 'label': 'Tunisia'},
  {'value': 'TR', 'label': 'Turkey'},
  {'value': 'TM', 'label': 'Turkmenistan'},
  {'value': 'TV', 'label': 'Tuvalu'},
  {'value': 'UG', 'label': 'Uganda'},
  {'value': 'UA', 'label': 'Ukraine'},
  {'value': 'AE', 'label': 'United Arab Emirates'},
  {'value': 'GB', 'label': 'United Kingdom'},
  {'value': 'US', 'label': 'United States'},
  {'value': 'UY', 'label': 'Uruguay'},
  {'value': 'UZ', 'label': 'Uzbekistan'},
  {'value': 'VU', 'label': 'Vanuatu'},
  {'value': 'VA', 'label': 'Vatican City'},
  {'value': 'VE', 'label': 'Venezuela'},
  {'value': 'VN', 'label': 'Vietnam'},
  {'value': 'YE', 'label': 'Yemen'},
  {'value': 'ZM', 'label': 'Zambia'},
  {'value': 'ZW', 'label': 'Zimbabwe'},
];
