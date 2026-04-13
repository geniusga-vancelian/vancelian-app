import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Password strength level for [PasswordStrengthIndicator].
enum PasswordStrength { strong, medium, weak, none }

/// Visual indicator for password strength with colored bars and label.
///
/// Figma spec:
///   - 3 bars: flex 1, height 4px, border-radius 2px, gap 4px
///   - Strong: 3 bars #34C759, label "Strong"
///   - Medium: 2 bars #FF8D28, label "So-so"
///   - Weak: 1 bar #FF2D55, label "Weak"
///   - None: 0 active bars, all #C7C7CC
///   - Label: Inter Regular 13px, color #8E8E93, tracking -0.08px
class PasswordStrengthIndicator extends StatelessWidget {
  const PasswordStrengthIndicator({
    super.key,
    required this.strength,
    this.showLabel = true,
  });

  final PasswordStrength strength;
  final bool showLabel;

  static const _inactiveColor = Color(0xFFC7C7CC);
  static const _labelColor = Color(0xFF8E8E93);

  int get _activeBars {
    switch (strength) {
      case PasswordStrength.strong:
        return 3;
      case PasswordStrength.medium:
        return 2;
      case PasswordStrength.weak:
        return 1;
      case PasswordStrength.none:
        return 0;
    }
  }

  Color get _activeColor {
    switch (strength) {
      case PasswordStrength.strong:
        return const Color(0xFF34C759);
      case PasswordStrength.medium:
        return const Color(0xFFFF8D28);
      case PasswordStrength.weak:
        return const Color(0xFFFF2D55);
      case PasswordStrength.none:
        return _inactiveColor;
    }
  }

  String get _label {
    switch (strength) {
      case PasswordStrength.strong:
        return 'Strong';
      case PasswordStrength.medium:
        return 'So-so';
      case PasswordStrength.weak:
        return 'Weak';
      case PasswordStrength.none:
        return '';
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Row(
          children: [
            for (int i = 0; i < 3; i++) ...[
              if (i > 0) const SizedBox(width: 4),
              Expanded(
                child: Container(
                  height: 4,
                  decoration: BoxDecoration(
                    color: i < _activeBars ? _activeColor : _inactiveColor,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
            ],
          ],
        ),
        if (showLabel && _label.isNotEmpty) ...[
          const SizedBox(height: 2),
          Text(
            _label,
            style: GoogleFonts.inter(
              fontSize: 13,
              fontWeight: FontWeight.w400,
              height: 16 / 13,
              letterSpacing: -0.08,
              color: _labelColor,
            ),
          ),
        ],
      ],
    );
  }
}
