import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../atoms/app_colors.dart';

/// Date picker that shows a tappable card (matching AppTextInput style)
/// and opens the native Material date picker on tap.
///
/// Display format: dd/MM/yyyy
class AppDatePicker extends StatelessWidget {
  const AppDatePicker({
    super.key,
    required this.label,
    this.value,
    required this.onChanged,
    this.required = false,
    this.enabled = true,
    this.firstDate,
    this.lastDate,
    this.error,
  });

  final String label;
  final DateTime? value;
  final ValueChanged<DateTime?> onChanged;
  final bool required;
  final bool enabled;
  final DateTime? firstDate;
  final DateTime? lastDate;
  final String? error;

  static const _radius = 16.0;
  static const _labelColor = Color(0xFFB3B3B3);
  static const _placeholderColor = Color(0xFF8E8E93);
  static const _errorColor = Color(0xFFFF2D55);

  bool get _hasError => error != null && error!.isNotEmpty;

  String get _formattedDate {
    if (value == null) return '';
    final d = value!;
    return '${d.day.toString().padLeft(2, '0')}/'
        '${d.month.toString().padLeft(2, '0')}/'
        '${d.year}';
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        GestureDetector(
          onTap: enabled ? () => _pickDate(context) : null,
          child: Container(
            decoration: BoxDecoration(
              color: enabled ? Colors.white : const Color(0xFFF5F5F5),
              borderRadius: BorderRadius.circular(_radius),
              border: _hasError ? Border.all(color: _errorColor) : null,
            ),
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
            child: Row(
              children: [
                Expanded(
                  child: value != null
                      ? Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(
                              required ? '$label *' : label,
                              style: GoogleFonts.inter(
                                fontSize: 11,
                                fontWeight: FontWeight.w600,
                                height: 13 / 11,
                                letterSpacing: 0.06,
                                color: _labelColor,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              _formattedDate,
                              style: GoogleFonts.inter(
                                fontSize: 17,
                                fontWeight: FontWeight.w600,
                                height: 22 / 17,
                                letterSpacing: -0.43,
                                color: Colors.black,
                              ),
                            ),
                          ],
                        )
                      : Text(
                          required ? '$label *' : label,
                          style: GoogleFonts.inter(
                            fontSize: 17,
                            fontWeight: FontWeight.w600,
                            height: 22 / 17,
                            letterSpacing: -0.43,
                            color: _placeholderColor,
                          ),
                        ),
                ),
                Icon(
                  Icons.calendar_today_rounded,
                  size: 20,
                  color: enabled ? _placeholderColor : const Color(0xFF808080),
                ),
              ],
            ),
          ),
        ),
        if (_hasError)
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text(
              error!,
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

  Future<void> _pickDate(BuildContext context) async {
    final now = DateTime.now();
    final picked = await showDatePicker(
      context: context,
      initialDate: value ?? now,
      firstDate: firstDate ?? DateTime(1900),
      lastDate: lastDate ?? now,
      builder: (ctx, child) {
        return Theme(
          data: Theme.of(ctx).copyWith(
            colorScheme: const ColorScheme.light(
              primary: AppColors.indigo,
              onPrimary: Colors.white,
              surface: Colors.white,
              onSurface: Colors.black,
            ),
          ),
          child: child!,
        );
      },
    );
    if (picked != null) onChanged(picked);
  }
}
