import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';

import '../atoms/app_colors.dart';

/// Three inline text fields for manual date entry (DD / MM / YYYY).
///
/// Provides per-field and cross-field validation:
///   - Day:   01 – 31 (adjusted for month & leap year when month is known)
///   - Month: 01 – 12
///   - Year:  ≥ 1900
///   - [isBirthDate]: the date cannot be in the future
///
/// Fires [onChanged] with a [DateTime] whenever all three fields form a valid
/// date, or `null` when incomplete / invalid.
class AppDateInput extends StatefulWidget {
  const AppDateInput({
    super.key,
    this.label,
    this.value,
    required this.onChanged,
    this.isBirthDate = false,
    this.required = false,
    this.enabled = true,
    this.error,
    this.dayLabel = 'Day',
    this.monthLabel = 'Month',
    this.yearLabel = 'Year',
  });

  final String? label;
  final DateTime? value;
  final ValueChanged<DateTime?> onChanged;
  final bool isBirthDate;
  final bool required;
  final bool enabled;
  final String? error;
  final String dayLabel;
  final String monthLabel;
  final String yearLabel;

  @override
  State<AppDateInput> createState() => _AppDateInputState();
}

class _AppDateInputState extends State<AppDateInput> {
  late final TextEditingController _dayCtrl;
  late final TextEditingController _monthCtrl;
  late final TextEditingController _yearCtrl;

  final _dayFocus = FocusNode();
  final _monthFocus = FocusNode();
  final _yearFocus = FocusNode();

  int _focusedField = -1; // 0=day, 1=month, 2=year, -1=none
  String? _validationError;

  static const _radius = 16.0;
  static const _containerHeight = 56.0;
  static const _labelColor = Color(0xFF8E8E93);
  static const _errorColor = Color(0xFFFF2D55);
  static const _descColor = Color(0xFF808080);
  static const _gap = 8.0;

  @override
  void initState() {
    super.initState();
    _dayCtrl = TextEditingController(
      text: widget.value != null
          ? widget.value!.day.toString().padLeft(2, '0')
          : '',
    );
    _monthCtrl = TextEditingController(
      text: widget.value != null
          ? widget.value!.month.toString().padLeft(2, '0')
          : '',
    );
    _yearCtrl = TextEditingController(
      text: widget.value != null ? widget.value!.year.toString() : '',
    );

    _dayFocus.addListener(() => _onFocusChanged(0));
    _monthFocus.addListener(() => _onFocusChanged(1));
    _yearFocus.addListener(() => _onFocusChanged(2));
  }

  @override
  void didUpdateWidget(covariant AppDateInput oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.value != oldWidget.value && widget.value != null) {
      final d = widget.value!;
      _setTextIfDifferent(_dayCtrl, d.day.toString().padLeft(2, '0'));
      _setTextIfDifferent(_monthCtrl, d.month.toString().padLeft(2, '0'));
      _setTextIfDifferent(_yearCtrl, d.year.toString());
    }
  }

  void _setTextIfDifferent(TextEditingController ctrl, String value) {
    if (ctrl.text != value) {
      ctrl.text = value;
    }
  }

  @override
  void dispose() {
    _dayCtrl.dispose();
    _monthCtrl.dispose();
    _yearCtrl.dispose();
    _dayFocus.dispose();
    _monthFocus.dispose();
    _yearFocus.dispose();
    super.dispose();
  }

  void _onFocusChanged(int field) {
    final hasFocus = [_dayFocus, _monthFocus, _yearFocus][field].hasFocus;
    setState(() {
      _focusedField = hasFocus ? field : -1;
      if (!hasFocus) _validate();
    });
  }

  // ── Validation ──

  int _maxDayForMonth(int month, int year) {
    if (month < 1 || month > 12) return 31;
    const daysInMonth = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    if (month == 2) {
      final isLeap =
          (year % 4 == 0 && year % 100 != 0) || (year % 400 == 0);
      return isLeap ? 29 : 28;
    }
    return daysInMonth[month - 1];
  }

  void _validate() {
    final day = int.tryParse(_dayCtrl.text);
    final month = int.tryParse(_monthCtrl.text);
    final year = int.tryParse(_yearCtrl.text);

    final allEmpty =
        _dayCtrl.text.isEmpty && _monthCtrl.text.isEmpty && _yearCtrl.text.isEmpty;

    if (allEmpty) {
      _validationError = null;
      widget.onChanged(null);
      return;
    }

    if (month != null && (month < 1 || month > 12)) {
      _validationError = 'Month must be between 01 and 12';
      widget.onChanged(null);
      return;
    }

    if (year != null && _yearCtrl.text.isNotEmpty && year < 1900) {
      _validationError = 'Year must be 1900 or later';
      widget.onChanged(null);
      return;
    }

    if (day != null) {
      final maxDay = _maxDayForMonth(month ?? 1, year ?? 2000);
      if (day < 1 || day > maxDay) {
        final monthName = month != null ? ' for this month' : '';
        _validationError = 'Day must be between 01 and $maxDay$monthName';
        widget.onChanged(null);
        return;
      }
    }

    if (day != null && month != null && year != null && year >= 1900) {
      final maxDay = _maxDayForMonth(month, year);
      if (day >= 1 && day <= maxDay) {
        final date = DateTime(year, month, day);
        final today = DateTime.now();
        final todayDate = DateTime(today.year, today.month, today.day);
        if (widget.isBirthDate && !date.isBefore(todayDate)) {
          _validationError = 'Date of birth must be before today';
          widget.onChanged(null);
          return;
        }
        _validationError = null;
        widget.onChanged(date);
        return;
      }
    }

    _validationError = null;
    widget.onChanged(null);
  }

  // ── Auto-advance ──

  void _onDayChanged(String v) {
    setState(() {});
    if (v.length == 2) _monthFocus.requestFocus();
    _validate();
  }

  void _onMonthChanged(String v) {
    setState(() {});
    if (v.length == 2) _yearFocus.requestFocus();
    _validate();
  }

  void _onYearChanged(String v) {
    setState(() {});
    _validate();
  }

  // ── Error resolution ──

  bool get _hasError =>
      (widget.error != null && widget.error!.isNotEmpty) ||
      (_validationError != null && _validationError!.isNotEmpty);

  String? get _displayError => widget.error ?? _validationError;

  // ── Build ──

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        if (widget.label != null)
          Padding(
            padding: const EdgeInsets.only(bottom: 6, left: 4),
            child: Text(
              widget.required ? '${widget.label} *' : widget.label!,
              style: GoogleFonts.inter(
                fontSize: 13,
                fontWeight: FontWeight.w600,
                height: 16 / 13,
                letterSpacing: -0.08,
                color: _descColor,
              ),
            ),
          ),
        Row(
          children: [
            Expanded(
              flex: 3,
              child: _buildField(
                controller: _dayCtrl,
                focusNode: _dayFocus,
                label: widget.dayLabel,
                maxLength: 2,
                fieldIndex: 0,
                onChanged: _onDayChanged,
              ),
            ),
            const SizedBox(width: _gap),
            Expanded(
              flex: 3,
              child: _buildField(
                controller: _monthCtrl,
                focusNode: _monthFocus,
                label: widget.monthLabel,
                maxLength: 2,
                fieldIndex: 1,
                onChanged: _onMonthChanged,
              ),
            ),
            const SizedBox(width: _gap),
            Expanded(
              flex: 4,
              child: _buildField(
                controller: _yearCtrl,
                focusNode: _yearFocus,
                label: widget.yearLabel,
                maxLength: 4,
                fieldIndex: 2,
                onChanged: _onYearChanged,
              ),
            ),
          ],
        ),
        if (_hasError)
          Padding(
            padding: const EdgeInsets.only(top: 4, left: 4),
            child: Text(
              _displayError!,
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

  Widget _buildField({
    required TextEditingController controller,
    required FocusNode focusNode,
    required String label,
    required int maxLength,
    required int fieldIndex,
    required ValueChanged<String> onChanged,
  }) {
    final isFocused = _focusedField == fieldIndex;
    final hasText = controller.text.isNotEmpty;
    final isFloating = isFocused || hasText;

    Color borderColor;
    if (_hasError) {
      borderColor = _errorColor;
    } else if (isFocused) {
      borderColor = AppColors.indigo;
    } else {
      borderColor = Colors.white;
    }

    return AnimatedContainer(
      duration: const Duration(milliseconds: 250),
      curve: Curves.easeInOut,
      height: _containerHeight,
      decoration: BoxDecoration(
        color: widget.enabled ? Colors.white : const Color(0xFFF5F5F5),
        borderRadius: BorderRadius.circular(_radius),
        border: Border.all(color: borderColor, width: 1.5),
      ),
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Stack(
        children: [
          Positioned.fill(
            child: Theme(
              data: Theme.of(context).copyWith(
                textSelectionTheme: TextSelectionThemeData(
                  selectionColor: AppColors.indigo.withValues(alpha: 0.15),
                  cursorColor: AppColors.indigo,
                  selectionHandleColor: AppColors.indigo,
                ),
              ),
              child: TextField(
                controller: controller,
                focusNode: focusNode,
                enabled: widget.enabled,
                cursorColor: AppColors.indigo,
                keyboardType: TextInputType.number,
                textInputAction: fieldIndex < 2
                    ? TextInputAction.next
                    : TextInputAction.done,
                inputFormatters: [
                  FilteringTextInputFormatter.digitsOnly,
                  LengthLimitingTextInputFormatter(maxLength),
                ],
                onChanged: onChanged,
                style: GoogleFonts.inter(
                  fontSize: 17,
                  fontWeight: FontWeight.w600,
                  height: 1.0,
                  letterSpacing: -0.43,
                  color: Colors.black,
                ),
                decoration: const InputDecoration(
                  border: InputBorder.none,
                  enabledBorder: InputBorder.none,
                  focusedBorder: InputBorder.none,
                  isDense: true,
                  filled: false,
                  contentPadding: EdgeInsets.only(top: 24, bottom: 4),
                  counterText: '',
                ),
              ),
            ),
          ),
          AnimatedPositioned(
            duration: const Duration(milliseconds: 150),
            curve: Curves.easeInOut,
            top: isFloating ? 8 : 16,
            left: 0,
            child: IgnorePointer(
              child: AnimatedDefaultTextStyle(
                duration: const Duration(milliseconds: 150),
                curve: Curves.easeInOut,
                style: isFloating
                    ? GoogleFonts.inter(
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                        height: 13 / 11,
                        letterSpacing: 0.06,
                        color: _hasError
                            ? _errorColor
                            : const Color(0xFFD1D1D6),
                      )
                    : GoogleFonts.inter(
                        fontSize: 17,
                        fontWeight: FontWeight.w600,
                        height: 22 / 17,
                        letterSpacing: -0.43,
                        color: _labelColor,
                      ),
                child: Text(label),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
