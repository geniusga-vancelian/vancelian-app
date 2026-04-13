import 'package:circle_flags/circle_flags.dart';
import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';

import '../../core/jank_trace.dart';
import '../atoms/app_colors.dart';
import '../atoms/app_spacing.dart';
import '../atoms/grabber.dart';
import 'app_search_input.dart';
import 'app_sheet_list_item.dart';
import 'sheet_title_bar.dart';

/// Combined phone input: country-code picker (flag + dial code) on the left,
/// phone number text field on the right, on a single row.
///
/// The left part opens a bottom-sheet country selector (no chevron).
/// The right part is a standard text field with phone keyboard.
///
/// Returns the full value via two callbacks:
///   - [onCountryChanged] → ISO alpha-2 code (e.g. "FR")
///   - [onPhoneChanged]   → national / free-form input as typed (not canonical E.164;
///     the backend parses and normalizes for registration submit).
class AppPhoneInput extends StatefulWidget {
  const AppPhoneInput({
    super.key,
    this.label = 'Enter your phone',
    this.countryCode,
    this.phoneController,
    this.phoneFocusNode,
    this.onCountryChanged,
    this.onPhoneChanged,
    this.error,
    this.required = false,
    this.enabled = true,
    this.textInputAction,
    this.allowedPhoneCountries,
    this.defaultPhoneCountryIso2,
    this.showInlineError = true,
  });

  final String label;

  /// When false, [error] still affects the field border but no text under the row.
  final bool showInlineError;

  /// ISO alpha-2 country code (e.g. "FR", "US"). Defaults to "FR" if null.
  final String? countryCode;

  /// When set by the registration API, restricts the picker to these countries
  /// (order preserved). Each map: iso2, dial_code, label_en, label_fr, is_default.
  final List<Map<String, dynamic>>? allowedPhoneCountries;

  /// Default ISO2 when [countryCode] is null (from backend `default_phone_country`).
  final String? defaultPhoneCountryIso2;
  final TextEditingController? phoneController;
  final FocusNode? phoneFocusNode;
  final ValueChanged<String>? onCountryChanged;
  final ValueChanged<String>? onPhoneChanged;
  final String? error;
  final bool required;
  final bool enabled;
  final TextInputAction? textInputAction;

  @override
  State<AppPhoneInput> createState() => _AppPhoneInputState();
}

class _AppPhoneInputState extends State<AppPhoneInput> {
  late TextEditingController _ctrl;
  FocusNode? _internalFocusNode;
  bool _hasFocus = false;
  bool _isPickerOpen = false;

  static const _containerHeight = 56.0;
  static const _radius = 16.0;
  static const _labelColor = Color(0xFF8E8E93);
  static const _errorColor = Color(0xFFFF2D55);

  String get _resolvedCountry {
    final cc = widget.countryCode;
    if (cc != null && cc.isNotEmpty) return cc.toUpperCase();
    final d = widget.defaultPhoneCountryIso2;
    if (d != null && d.isNotEmpty) return d.toUpperCase();
    return 'FR';
  }

  String get _dialCode {
    final iso = _resolvedCountry;
    final raw = widget.allowedPhoneCountries;
    if (raw != null) {
      for (final e in raw) {
        final m = Map<String, dynamic>.from(e);
        if ((m['iso2'] ?? '').toString().toUpperCase() != iso) continue;
        final d = (m['dial_code'] ?? '').toString();
        if (d.isNotEmpty) return d;
        break;
      }
    }
    return _countryDialCodes[iso] ?? '+33';
  }

  List<_PhoneCountry> _pickerCountries(BuildContext context) {
    final raw = widget.allowedPhoneCountries;
    if (raw == null || raw.isEmpty) return _phoneCountries;
    final byIso = {for (final c in _phoneCountries) c.iso: c};
    final lang = Localizations.maybeLocaleOf(context)?.languageCode ?? 'en';
    final useFr = lang.startsWith('fr');
    final out = <_PhoneCountry>[];
    for (final e in raw) {
      final m = Map<String, dynamic>.from(e);
      final iso = (m['iso2'] ?? '').toString().toUpperCase();
      if (iso.isEmpty) continue;
      var dial = (m['dial_code'] ?? '').toString();
      if (dial.isEmpty) dial = phoneDialCodeForIso(iso);
      late final String name;
      if (useFr) {
        final fr = m['label_fr']?.toString();
        if (fr != null && fr.isNotEmpty) {
          name = fr;
        } else {
          final en = m['label_en']?.toString();
          name =
              (en != null && en.isNotEmpty) ? en : (byIso[iso]?.name ?? iso);
        }
      } else {
        final en = m['label_en']?.toString();
        name = (en != null && en.isNotEmpty) ? en : (byIso[iso]?.name ?? iso);
      }
      out.add(_PhoneCountry(iso, name, dial));
    }
    return out.isEmpty ? _phoneCountries : out;
  }

  FocusNode get _focusNode =>
      widget.phoneFocusNode ?? (_internalFocusNode ??= FocusNode());

  bool get _hasError => widget.error != null && widget.error!.isNotEmpty;

  TextStyle _dialCodeStyle(BuildContext context) {
    final base = Theme.of(context).textTheme.bodyLarge;
    return (base ?? const TextStyle()).copyWith(
      fontSize: 17,
      fontWeight: FontWeight.w600,
      height: 22 / 17,
      letterSpacing: -0.43,
      color: Colors.black,
    );
  }

  TextStyle _phoneFieldStyle(BuildContext context) {
    final base = Theme.of(context).textTheme.bodyLarge;
    return (base ?? const TextStyle()).copyWith(
      fontSize: 17,
      fontWeight: FontWeight.w600,
      height: 1.0,
      letterSpacing: -0.43,
      color: Colors.black,
    );
  }

  TextStyle _hintStyle(BuildContext context) {
    final base = Theme.of(context).textTheme.bodyLarge;
    return (base ?? const TextStyle()).copyWith(
      fontSize: 17,
      fontWeight: FontWeight.w600,
      height: 22 / 17,
      letterSpacing: -0.43,
      color: _labelColor,
    );
  }

  TextStyle _errorLineStyle(BuildContext context) {
    final base = Theme.of(context).textTheme.bodySmall;
    return (base ?? const TextStyle()).copyWith(
      fontSize: 13,
      fontWeight: FontWeight.w400,
      height: 16 / 13,
      letterSpacing: -0.08,
      color: _errorColor,
    );
  }

  @override
  void initState() {
    super.initState();
    _ctrl = widget.phoneController ?? TextEditingController();
    _focusNode.addListener(_onFocusChange);
  }

  @override
  void didUpdateWidget(covariant AppPhoneInput old) {
    super.didUpdateWidget(old);
    if (old.phoneFocusNode != widget.phoneFocusNode) {
      (old.phoneFocusNode ?? _internalFocusNode)
          ?.removeListener(_onFocusChange);
      _focusNode.addListener(_onFocusChange);
      _hasFocus = _focusNode.hasFocus;
    }
  }

  @override
  void dispose() {
    if (widget.phoneController == null) _ctrl.dispose();
    _focusNode.removeListener(_onFocusChange);
    _internalFocusNode?.dispose();
    super.dispose();
  }

  void _onFocusChange() {
    if (_focusNode.hasFocus != _hasFocus) {
      setState(() => _hasFocus = _focusNode.hasFocus);
    }
    if (_focusNode.hasFocus) {
      JankTrace.phoneFieldFocusStart();
      SchedulerBinding.instance.addPostFrameCallback((_) {
        if (mounted) JankTrace.phoneFieldFocusFirstFrame();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final displayLabel =
        widget.required ? '${widget.label} *' : widget.label;

    const disabledBg = Color(0xFFF5F5F5);
    const enabledBg = Colors.white;
    final bg = widget.enabled ? enabledBg : disabledBg;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        SizedBox(
          height: _containerHeight,
          child: Row(
            children: [
              // ── Country code button ──
              GestureDetector(
                onTap: widget.enabled ? () => _showPicker(context) : null,
                behavior: HitTestBehavior.opaque,
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 250),
                  curve: Curves.easeInOut,
                  height: _containerHeight,
                  padding: const EdgeInsets.symmetric(horizontal: 14),
                  decoration: BoxDecoration(
                    color: bg,
                    borderRadius: BorderRadius.circular(_radius),
                    border: Border.all(
                      color: _isPickerOpen ? AppColors.indigo : Colors.white,
                      width: 1.5,
                    ),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      CircleFlag(
                        _resolvedCountry.toLowerCase(),
                        size: 28,
                      ),
                      const SizedBox(width: 8),
                      Text(
                        _dialCode,
                        style: _dialCodeStyle(context),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(width: 8),
              // ── Phone number field ──
              Expanded(
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 250),
                  curve: Curves.easeInOut,
                  height: _containerHeight,
                  decoration: BoxDecoration(
                    color: bg,
                    borderRadius: BorderRadius.circular(_radius),
                    border: Border.all(
                      color: _hasError
                          ? _errorColor
                          : _hasFocus
                              ? AppColors.indigo
                              : Colors.white,
                      width: 1.5,
                    ),
                  ),
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: Theme(
                    data: Theme.of(context).copyWith(
                      textSelectionTheme: TextSelectionThemeData(
                        selectionColor:
                            AppColors.indigo.withValues(alpha: 0.15),
                        cursorColor: AppColors.indigo,
                        selectionHandleColor: AppColors.indigo,
                      ),
                    ),
                    child: TextField(
                      controller: _ctrl,
                      focusNode: _focusNode,
                      enabled: widget.enabled,
                      cursorColor: AppColors.indigo,
                      keyboardType: TextInputType.phone,
                      textInputAction: widget.textInputAction,
                      expands: true,
                      maxLines: null,
                      textAlignVertical: TextAlignVertical.center,
                      onChanged: (v) {
                        widget.onPhoneChanged?.call(v);
                        setState(() {});
                      },
                      style: _phoneFieldStyle(context),
                      decoration: InputDecoration(
                        border: InputBorder.none,
                        enabledBorder: InputBorder.none,
                        focusedBorder: InputBorder.none,
                        isDense: true,
                        filled: false,
                        contentPadding: EdgeInsets.zero,
                        hintText: displayLabel,
                        hintStyle: _hintStyle(context),
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
        if (widget.showInlineError && _hasError)
          Padding(
            padding: const EdgeInsets.only(top: 4, left: 4),
            child: Text(
              widget.error!,
              style: _errorLineStyle(context),
            ),
          ),
      ],
    );
  }

  void _showPicker(BuildContext context) {
    JankTrace.tap('modal_phone_country');
    setState(() => _isPickerOpen = true);
    showModalBottomSheet<String>(
      context: context,
      backgroundColor: Colors.white,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (ctx) => _PhoneCodePickerSheet(
        selectedCountry: _resolvedCountry,
        countries: _pickerCountries(context),
      ),
    ).then((selected) {
      if (mounted) setState(() => _isPickerOpen = false);
      if (selected != null) widget.onCountryChanged?.call(selected);
    });
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Bottom-sheet picker
// ─────────────────────────────────────────────────────────────────────────────

class _PhoneCodePickerSheet extends StatefulWidget {
  const _PhoneCodePickerSheet({
    required this.selectedCountry,
    required this.countries,
  });

  final String selectedCountry;
  final List<_PhoneCountry> countries;

  @override
  State<_PhoneCodePickerSheet> createState() => _PhoneCodePickerSheetState();
}

class _PhoneCodePickerSheetState extends State<_PhoneCodePickerSheet> {
  late final TextEditingController _searchCtrl;
  late final ScrollController _scrollCtrl;
  String _query = '';

  static const _itemExtent = 72.0;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      JankTrace.markModalFirstFrame('PhoneCodePickerSheet');
    });
    _searchCtrl = TextEditingController();

    final selectedIdx = widget.countries.indexWhere(
      (c) => c.iso == widget.selectedCountry,
    );
    final offset =
        selectedIdx > 2 ? (selectedIdx - 2) * _itemExtent : 0.0;
    _scrollCtrl = ScrollController(initialScrollOffset: offset);
  }

  @override
  void dispose() {
    _searchCtrl.dispose();
    _scrollCtrl.dispose();
    super.dispose();
  }

  List<_PhoneCountry> get _filtered {
    if (_query.isEmpty) return widget.countries;
    final q = _query.toLowerCase();
    return widget.countries.where((c) {
      return c.name.toLowerCase().contains(q) ||
          c.iso.toLowerCase().contains(q) ||
          c.dial.contains(q);
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
            title: 'Country code',
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
                final isSelected = c.iso == widget.selectedCountry;
                return AppSheetListItem(
                  title: c.name,
                  subtitle: c.dial,
                  leading: CircleFlag(c.iso.toLowerCase(), size: 36),
                  selected: isSelected,
                  showChevron: false,
                  onTap: () => Navigator.pop(context, c.iso),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// Data model + country list with dial codes
// ─────────────────────────────────────────────────────────────────────────────

class _PhoneCountry {
  const _PhoneCountry(this.iso, this.name, this.dial);
  final String iso;
  final String name;
  final String dial;
}

/// ISO alpha-2 → international dial code mapping.
const _countryDialCodes = <String, String>{
  'AF': '+93',
  'AL': '+355',
  'DZ': '+213',
  'AD': '+376',
  'AO': '+244',
  'AG': '+1',
  'AR': '+54',
  'AM': '+374',
  'AU': '+61',
  'AT': '+43',
  'AZ': '+994',
  'BS': '+1',
  'BH': '+973',
  'BD': '+880',
  'BB': '+1',
  'BY': '+375',
  'BE': '+32',
  'BZ': '+501',
  'BJ': '+229',
  'BT': '+975',
  'BO': '+591',
  'BA': '+387',
  'BW': '+267',
  'BR': '+55',
  'BN': '+673',
  'BG': '+359',
  'BF': '+226',
  'BI': '+257',
  'CV': '+238',
  'KH': '+855',
  'CM': '+237',
  'CA': '+1',
  'CF': '+236',
  'TD': '+235',
  'CL': '+56',
  'CN': '+86',
  'CO': '+57',
  'KM': '+269',
  'CG': '+242',
  'CD': '+243',
  'CR': '+506',
  'CI': '+225',
  'HR': '+385',
  'CU': '+53',
  'CY': '+357',
  'CZ': '+420',
  'DK': '+45',
  'DJ': '+253',
  'DM': '+1',
  'DO': '+1',
  'EC': '+593',
  'EG': '+20',
  'SV': '+503',
  'GQ': '+240',
  'ER': '+291',
  'EE': '+372',
  'SZ': '+268',
  'ET': '+251',
  'FJ': '+679',
  'FI': '+358',
  'FR': '+33',
  'GA': '+241',
  'GM': '+220',
  'GE': '+995',
  'DE': '+49',
  'GH': '+233',
  'GR': '+30',
  'GD': '+1',
  'GT': '+502',
  'GN': '+224',
  'GW': '+245',
  'GY': '+592',
  'HT': '+509',
  'HN': '+504',
  'HU': '+36',
  'IS': '+354',
  'IN': '+91',
  'ID': '+62',
  'IR': '+98',
  'IQ': '+964',
  'IE': '+353',
  'IL': '+972',
  'IT': '+39',
  'JM': '+1',
  'JP': '+81',
  'JO': '+962',
  'KZ': '+7',
  'KE': '+254',
  'KI': '+686',
  'KP': '+850',
  'KR': '+82',
  'KW': '+965',
  'KG': '+996',
  'LA': '+856',
  'LV': '+371',
  'LB': '+961',
  'LS': '+266',
  'LR': '+231',
  'LY': '+218',
  'LI': '+423',
  'LT': '+370',
  'LU': '+352',
  'MG': '+261',
  'MW': '+265',
  'MY': '+60',
  'MV': '+960',
  'ML': '+223',
  'MT': '+356',
  'MH': '+692',
  'MR': '+222',
  'MU': '+230',
  'MX': '+52',
  'FM': '+691',
  'MD': '+373',
  'MC': '+377',
  'MN': '+976',
  'ME': '+382',
  'MA': '+212',
  'MZ': '+258',
  'MM': '+95',
  'NA': '+264',
  'NR': '+674',
  'NP': '+977',
  'NL': '+31',
  'NZ': '+64',
  'NI': '+505',
  'NE': '+227',
  'NG': '+234',
  'MK': '+389',
  'NO': '+47',
  'OM': '+968',
  'PK': '+92',
  'PW': '+680',
  'PS': '+970',
  'PA': '+507',
  'PG': '+675',
  'PY': '+595',
  'PE': '+51',
  'PH': '+63',
  'PL': '+48',
  'PT': '+351',
  'QA': '+974',
  'RO': '+40',
  'RU': '+7',
  'RW': '+250',
  'KN': '+1',
  'LC': '+1',
  'VC': '+1',
  'WS': '+685',
  'SM': '+378',
  'ST': '+239',
  'SA': '+966',
  'SN': '+221',
  'RS': '+381',
  'SC': '+248',
  'SL': '+232',
  'SG': '+65',
  'SK': '+421',
  'SI': '+386',
  'SB': '+677',
  'SO': '+252',
  'ZA': '+27',
  'SS': '+211',
  'ES': '+34',
  'LK': '+94',
  'SD': '+249',
  'SR': '+597',
  'SE': '+46',
  'CH': '+41',
  'SY': '+963',
  'TW': '+886',
  'TJ': '+992',
  'TZ': '+255',
  'TH': '+66',
  'TL': '+670',
  'TG': '+228',
  'TO': '+676',
  'TT': '+1',
  'TN': '+216',
  'TR': '+90',
  'TM': '+993',
  'TV': '+688',
  'UG': '+256',
  'UA': '+380',
  'AE': '+971',
  'GB': '+44',
  'US': '+1',
  'UY': '+598',
  'UZ': '+998',
  'VU': '+678',
  'VA': '+39',
  'VE': '+58',
  'VN': '+84',
  'YE': '+967',
  'ZM': '+260',
  'ZW': '+263',
};

/// Indicatif international pour un pays ISO alpha-2 (ex. `FR` → `+33`).
String phoneDialCodeForIso(String iso) =>
    _countryDialCodes[iso.toUpperCase()] ?? '+33';

/// Sorted list for the picker sheet.
final List<_PhoneCountry> _phoneCountries = (() {
  final list = <_PhoneCountry>[
    const _PhoneCountry('AF', 'Afghanistan', '+93'),
    const _PhoneCountry('AL', 'Albania', '+355'),
    const _PhoneCountry('DZ', 'Algeria', '+213'),
    const _PhoneCountry('AD', 'Andorra', '+376'),
    const _PhoneCountry('AO', 'Angola', '+244'),
    const _PhoneCountry('AG', 'Antigua and Barbuda', '+1'),
    const _PhoneCountry('AR', 'Argentina', '+54'),
    const _PhoneCountry('AM', 'Armenia', '+374'),
    const _PhoneCountry('AU', 'Australia', '+61'),
    const _PhoneCountry('AT', 'Austria', '+43'),
    const _PhoneCountry('AZ', 'Azerbaijan', '+994'),
    const _PhoneCountry('BS', 'Bahamas', '+1'),
    const _PhoneCountry('BH', 'Bahrain', '+973'),
    const _PhoneCountry('BD', 'Bangladesh', '+880'),
    const _PhoneCountry('BB', 'Barbados', '+1'),
    const _PhoneCountry('BY', 'Belarus', '+375'),
    const _PhoneCountry('BE', 'Belgium', '+32'),
    const _PhoneCountry('BZ', 'Belize', '+501'),
    const _PhoneCountry('BJ', 'Benin', '+229'),
    const _PhoneCountry('BT', 'Bhutan', '+975'),
    const _PhoneCountry('BO', 'Bolivia', '+591'),
    const _PhoneCountry('BA', 'Bosnia and Herzegovina', '+387'),
    const _PhoneCountry('BW', 'Botswana', '+267'),
    const _PhoneCountry('BR', 'Brazil', '+55'),
    const _PhoneCountry('BN', 'Brunei', '+673'),
    const _PhoneCountry('BG', 'Bulgaria', '+359'),
    const _PhoneCountry('BF', 'Burkina Faso', '+226'),
    const _PhoneCountry('BI', 'Burundi', '+257'),
    const _PhoneCountry('CV', 'Cabo Verde', '+238'),
    const _PhoneCountry('KH', 'Cambodia', '+855'),
    const _PhoneCountry('CM', 'Cameroon', '+237'),
    const _PhoneCountry('CA', 'Canada', '+1'),
    const _PhoneCountry('CF', 'Central African Republic', '+236'),
    const _PhoneCountry('TD', 'Chad', '+235'),
    const _PhoneCountry('CL', 'Chile', '+56'),
    const _PhoneCountry('CN', 'China', '+86'),
    const _PhoneCountry('CO', 'Colombia', '+57'),
    const _PhoneCountry('KM', 'Comoros', '+269'),
    const _PhoneCountry('CG', 'Congo', '+242'),
    const _PhoneCountry('CD', 'Congo (DRC)', '+243'),
    const _PhoneCountry('CR', 'Costa Rica', '+506'),
    const _PhoneCountry('CI', "Côte d'Ivoire", '+225'),
    const _PhoneCountry('HR', 'Croatia', '+385'),
    const _PhoneCountry('CU', 'Cuba', '+53'),
    const _PhoneCountry('CY', 'Cyprus', '+357'),
    const _PhoneCountry('CZ', 'Czech Republic', '+420'),
    const _PhoneCountry('DK', 'Denmark', '+45'),
    const _PhoneCountry('DJ', 'Djibouti', '+253'),
    const _PhoneCountry('DM', 'Dominica', '+1'),
    const _PhoneCountry('DO', 'Dominican Republic', '+1'),
    const _PhoneCountry('EC', 'Ecuador', '+593'),
    const _PhoneCountry('EG', 'Egypt', '+20'),
    const _PhoneCountry('SV', 'El Salvador', '+503'),
    const _PhoneCountry('GQ', 'Equatorial Guinea', '+240'),
    const _PhoneCountry('ER', 'Eritrea', '+291'),
    const _PhoneCountry('EE', 'Estonia', '+372'),
    const _PhoneCountry('SZ', 'Eswatini', '+268'),
    const _PhoneCountry('ET', 'Ethiopia', '+251'),
    const _PhoneCountry('FJ', 'Fiji', '+679'),
    const _PhoneCountry('FI', 'Finland', '+358'),
    const _PhoneCountry('FR', 'France', '+33'),
    const _PhoneCountry('GA', 'Gabon', '+241'),
    const _PhoneCountry('GM', 'Gambia', '+220'),
    const _PhoneCountry('GE', 'Georgia', '+995'),
    const _PhoneCountry('DE', 'Germany', '+49'),
    const _PhoneCountry('GH', 'Ghana', '+233'),
    const _PhoneCountry('GR', 'Greece', '+30'),
    const _PhoneCountry('GD', 'Grenada', '+1'),
    const _PhoneCountry('GT', 'Guatemala', '+502'),
    const _PhoneCountry('GN', 'Guinea', '+224'),
    const _PhoneCountry('GW', 'Guinea-Bissau', '+245'),
    const _PhoneCountry('GY', 'Guyana', '+592'),
    const _PhoneCountry('HT', 'Haiti', '+509'),
    const _PhoneCountry('HN', 'Honduras', '+504'),
    const _PhoneCountry('HU', 'Hungary', '+36'),
    const _PhoneCountry('IS', 'Iceland', '+354'),
    const _PhoneCountry('IN', 'India', '+91'),
    const _PhoneCountry('ID', 'Indonesia', '+62'),
    const _PhoneCountry('IR', 'Iran', '+98'),
    const _PhoneCountry('IQ', 'Iraq', '+964'),
    const _PhoneCountry('IE', 'Ireland', '+353'),
    const _PhoneCountry('IL', 'Israel', '+972'),
    const _PhoneCountry('IT', 'Italy', '+39'),
    const _PhoneCountry('JM', 'Jamaica', '+1'),
    const _PhoneCountry('JP', 'Japan', '+81'),
    const _PhoneCountry('JO', 'Jordan', '+962'),
    const _PhoneCountry('KZ', 'Kazakhstan', '+7'),
    const _PhoneCountry('KE', 'Kenya', '+254'),
    const _PhoneCountry('KI', 'Kiribati', '+686'),
    const _PhoneCountry('KP', 'North Korea', '+850'),
    const _PhoneCountry('KR', 'South Korea', '+82'),
    const _PhoneCountry('KW', 'Kuwait', '+965'),
    const _PhoneCountry('KG', 'Kyrgyzstan', '+996'),
    const _PhoneCountry('LA', 'Laos', '+856'),
    const _PhoneCountry('LV', 'Latvia', '+371'),
    const _PhoneCountry('LB', 'Lebanon', '+961'),
    const _PhoneCountry('LS', 'Lesotho', '+266'),
    const _PhoneCountry('LR', 'Liberia', '+231'),
    const _PhoneCountry('LY', 'Libya', '+218'),
    const _PhoneCountry('LI', 'Liechtenstein', '+423'),
    const _PhoneCountry('LT', 'Lithuania', '+370'),
    const _PhoneCountry('LU', 'Luxembourg', '+352'),
    const _PhoneCountry('MG', 'Madagascar', '+261'),
    const _PhoneCountry('MW', 'Malawi', '+265'),
    const _PhoneCountry('MY', 'Malaysia', '+60'),
    const _PhoneCountry('MV', 'Maldives', '+960'),
    const _PhoneCountry('ML', 'Mali', '+223'),
    const _PhoneCountry('MT', 'Malta', '+356'),
    const _PhoneCountry('MH', 'Marshall Islands', '+692'),
    const _PhoneCountry('MR', 'Mauritania', '+222'),
    const _PhoneCountry('MU', 'Mauritius', '+230'),
    const _PhoneCountry('MX', 'Mexico', '+52'),
    const _PhoneCountry('FM', 'Micronesia', '+691'),
    const _PhoneCountry('MD', 'Moldova', '+373'),
    const _PhoneCountry('MC', 'Monaco', '+377'),
    const _PhoneCountry('MN', 'Mongolia', '+976'),
    const _PhoneCountry('ME', 'Montenegro', '+382'),
    const _PhoneCountry('MA', 'Morocco', '+212'),
    const _PhoneCountry('MZ', 'Mozambique', '+258'),
    const _PhoneCountry('MM', 'Myanmar', '+95'),
    const _PhoneCountry('NA', 'Namibia', '+264'),
    const _PhoneCountry('NR', 'Nauru', '+674'),
    const _PhoneCountry('NP', 'Nepal', '+977'),
    const _PhoneCountry('NL', 'Netherlands', '+31'),
    const _PhoneCountry('NZ', 'New Zealand', '+64'),
    const _PhoneCountry('NI', 'Nicaragua', '+505'),
    const _PhoneCountry('NE', 'Niger', '+227'),
    const _PhoneCountry('NG', 'Nigeria', '+234'),
    const _PhoneCountry('MK', 'North Macedonia', '+389'),
    const _PhoneCountry('NO', 'Norway', '+47'),
    const _PhoneCountry('OM', 'Oman', '+968'),
    const _PhoneCountry('PK', 'Pakistan', '+92'),
    const _PhoneCountry('PW', 'Palau', '+680'),
    const _PhoneCountry('PS', 'Palestine', '+970'),
    const _PhoneCountry('PA', 'Panama', '+507'),
    const _PhoneCountry('PG', 'Papua New Guinea', '+675'),
    const _PhoneCountry('PY', 'Paraguay', '+595'),
    const _PhoneCountry('PE', 'Peru', '+51'),
    const _PhoneCountry('PH', 'Philippines', '+63'),
    const _PhoneCountry('PL', 'Poland', '+48'),
    const _PhoneCountry('PT', 'Portugal', '+351'),
    const _PhoneCountry('QA', 'Qatar', '+974'),
    const _PhoneCountry('RO', 'Romania', '+40'),
    const _PhoneCountry('RU', 'Russia', '+7'),
    const _PhoneCountry('RW', 'Rwanda', '+250'),
    const _PhoneCountry('KN', 'Saint Kitts and Nevis', '+1'),
    const _PhoneCountry('LC', 'Saint Lucia', '+1'),
    const _PhoneCountry('VC', 'Saint Vincent and the Grenadines', '+1'),
    const _PhoneCountry('WS', 'Samoa', '+685'),
    const _PhoneCountry('SM', 'San Marino', '+378'),
    const _PhoneCountry('ST', 'São Tomé and Príncipe', '+239'),
    const _PhoneCountry('SA', 'Saudi Arabia', '+966'),
    const _PhoneCountry('SN', 'Senegal', '+221'),
    const _PhoneCountry('RS', 'Serbia', '+381'),
    const _PhoneCountry('SC', 'Seychelles', '+248'),
    const _PhoneCountry('SL', 'Sierra Leone', '+232'),
    const _PhoneCountry('SG', 'Singapore', '+65'),
    const _PhoneCountry('SK', 'Slovakia', '+421'),
    const _PhoneCountry('SI', 'Slovenia', '+386'),
    const _PhoneCountry('SB', 'Solomon Islands', '+677'),
    const _PhoneCountry('SO', 'Somalia', '+252'),
    const _PhoneCountry('ZA', 'South Africa', '+27'),
    const _PhoneCountry('SS', 'South Sudan', '+211'),
    const _PhoneCountry('ES', 'Spain', '+34'),
    const _PhoneCountry('LK', 'Sri Lanka', '+94'),
    const _PhoneCountry('SD', 'Sudan', '+249'),
    const _PhoneCountry('SR', 'Suriname', '+597'),
    const _PhoneCountry('SE', 'Sweden', '+46'),
    const _PhoneCountry('CH', 'Switzerland', '+41'),
    const _PhoneCountry('SY', 'Syria', '+963'),
    const _PhoneCountry('TW', 'Taiwan', '+886'),
    const _PhoneCountry('TJ', 'Tajikistan', '+992'),
    const _PhoneCountry('TZ', 'Tanzania', '+255'),
    const _PhoneCountry('TH', 'Thailand', '+66'),
    const _PhoneCountry('TL', 'Timor-Leste', '+670'),
    const _PhoneCountry('TG', 'Togo', '+228'),
    const _PhoneCountry('TO', 'Tonga', '+676'),
    const _PhoneCountry('TT', 'Trinidad and Tobago', '+1'),
    const _PhoneCountry('TN', 'Tunisia', '+216'),
    const _PhoneCountry('TR', 'Turkey', '+90'),
    const _PhoneCountry('TM', 'Turkmenistan', '+993'),
    const _PhoneCountry('TV', 'Tuvalu', '+688'),
    const _PhoneCountry('UG', 'Uganda', '+256'),
    const _PhoneCountry('UA', 'Ukraine', '+380'),
    const _PhoneCountry('AE', 'United Arab Emirates', '+971'),
    const _PhoneCountry('GB', 'United Kingdom', '+44'),
    const _PhoneCountry('US', 'United States', '+1'),
    const _PhoneCountry('UY', 'Uruguay', '+598'),
    const _PhoneCountry('UZ', 'Uzbekistan', '+998'),
    const _PhoneCountry('VU', 'Vanuatu', '+678'),
    const _PhoneCountry('VA', 'Vatican City', '+39'),
    const _PhoneCountry('VE', 'Venezuela', '+58'),
    const _PhoneCountry('VN', 'Vietnam', '+84'),
    const _PhoneCountry('YE', 'Yemen', '+967'),
    const _PhoneCountry('ZM', 'Zambia', '+260'),
    const _PhoneCountry('ZW', 'Zimbabwe', '+263'),
  ];
  return list;
})();
