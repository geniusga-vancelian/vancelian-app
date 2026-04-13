import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_spacing.dart';

/// Affichage centré d'un montant principal avec sous-titres.
///
/// Figma spec :
///   - Montant : Inter 34px / Bold / -0.136 tracking / lh 41
///   - Sous-titre : Inter 14px / SemiBold / lh 16
///   - Subtext : Inter 14px / SemiBold / #8E8E93 / lh 16
///   - Gap : 4px entre éléments
///   - Alignement : centré
class AmountDisplay extends StatelessWidget {
  const AmountDisplay({
    super.key,
    required this.amount,
    required this.subtitle,
    this.subtext,
    this.amountColor,
    this.subtitleColor,
  });

  final String amount;
  final String subtitle;
  final String? subtext;
  final Color? amountColor;
  final Color? subtitleColor;

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          amount,
          style: GoogleFonts.inter(
            fontSize: 34,
            fontWeight: FontWeight.w700,
            letterSpacing: -0.136,
            height: 41 / 34,
            color: amountColor ?? AppColors.textPrimary,
          ),
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: AppSpacing.xs),
        Text(
          subtitle,
          style: GoogleFonts.inter(
            fontSize: 14,
            fontWeight: FontWeight.w600,
            height: 16 / 14,
            color: subtitleColor ?? AppColors.textPrimary,
          ),
          textAlign: TextAlign.center,
        ),
        if (subtext != null && subtext!.isNotEmpty) ...[
          const SizedBox(height: AppSpacing.xs),
          Text(
            subtext!,
            style: GoogleFonts.inter(
              fontSize: 14,
              fontWeight: FontWeight.w600,
              height: 16 / 14,
              color: AppColors.gray,
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ],
    );
  }
}
