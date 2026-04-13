import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../atoms/app_colors.dart';

/// Radio button with 4 visual states matching Figma spec.
///
/// Figma spec:
///   - Size: 20x20px
///   - Default: circle border #D1D1D6
///   - Checked: outer border #6155F5 + inner filled circle #6155F5 (10px, 25% inset)
///   - Disabled: fill #EFEEFE, border #C7C7CC
///   - Disabled+Checked: #6155F5 circles + 20% black overlay
///   - Label: Inter Regular 13px, color #2C2C2E, gap 8px
class AppRadioButton extends StatelessWidget {
  const AppRadioButton({
    super.key,
    this.checked = false,
    this.disabled = false,
    this.label,
    this.onChanged,
  });

  final bool checked;
  final bool disabled;
  final String? label;
  final ValueChanged<bool>? onChanged;

  static const _size = 20.0;
  static const _innerSize = 10.0;
  static const _borderDefault = Color(0xFFD1D1D6);
  static const _borderDisabled = Color(0xFFC7C7CC);
  static const _fillDisabled = Color(0xFFEFEEFE);
  static const _labelColor = Color(0xFF2C2C2E);

  Widget _buildRadio() {
    if (disabled && !checked) {
      return Container(
        width: _size,
        height: _size,
        decoration: BoxDecoration(
          color: _fillDisabled,
          shape: BoxShape.circle,
          border: Border.all(color: _borderDisabled),
        ),
      );
    }

    if (disabled && checked) {
      return SizedBox(
        width: _size,
        height: _size,
        child: Stack(
          alignment: Alignment.center,
          children: [
            Container(
              width: _size,
              height: _size,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(color: AppColors.indigo),
              ),
            ),
            Container(
              width: _innerSize,
              height: _innerSize,
              decoration: const BoxDecoration(
                color: AppColors.indigo,
                shape: BoxShape.circle,
              ),
            ),
            Container(
              width: _size,
              height: _size,
              decoration: BoxDecoration(
                color: Colors.black.withValues(alpha: 0.2),
                shape: BoxShape.circle,
              ),
            ),
          ],
        ),
      );
    }

    if (checked) {
      return SizedBox(
        width: _size,
        height: _size,
        child: Stack(
          alignment: Alignment.center,
          children: [
            Container(
              width: _size,
              height: _size,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(color: AppColors.indigo),
              ),
            ),
            Container(
              width: _innerSize,
              height: _innerSize,
              decoration: const BoxDecoration(
                color: AppColors.indigo,
                shape: BoxShape.circle,
              ),
            ),
          ],
        ),
      );
    }

    return Container(
      width: _size,
      height: _size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        border: Border.all(color: _borderDefault),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final radio = _buildRadio();

    final child = label != null
        ? Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              radio,
              const SizedBox(width: 8),
              Text(
                label!,
                style: GoogleFonts.inter(
                  fontSize: 13,
                  fontWeight: FontWeight.w400,
                  height: 18 / 13,
                  letterSpacing: -0.08,
                  color: _labelColor,
                ),
              ),
            ],
          )
        : radio;

    return GestureDetector(
      onTap: disabled ? null : () => onChanged?.call(!checked),
      behavior: HitTestBehavior.opaque,
      child: child,
    );
  }
}
