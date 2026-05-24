import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_spacing.dart';
import 'app_otp_input.dart';

/// Bloc OTP SMS partagé avec le flow registration ([RegistrationPhoneSmsOtpPanel]) :
/// ligne de description + [AppOtpInput] 6 cases + renvoi (texte ou compte à rebours).
///
/// Ne duplique pas [AppOtpInput] — réutilise le même composant que l’inscription.
class AppSmsOtpVerificationBlock extends StatelessWidget {
  const AppSmsOtpVerificationBlock({
    super.key,
    this.description,
    this.descriptionLead = '',
    this.maskedTarget,
    required this.otpGeneration,
    required this.locked,
    required this.wrongCode,
    required this.resendCountdown,
    required this.resendInProgress,
    required this.onCompleted,
    required this.onResend,
    this.onOtpChanged,
    this.autofocus = true,
  });

  /// Si fourni, remplace la ligne « [descriptionLead] [maskedTarget] » (texte libre, ex. phrase unique avec e-mail en gras).
  final Widget? description;

  final String descriptionLead;
  final String? maskedTarget;
  final int otpGeneration;
  final bool locked;
  final bool wrongCode;
  final int resendCountdown;
  final bool resendInProgress;
  final ValueChanged<String> onCompleted;
  final VoidCallback onResend;
  final ValueChanged<String>? onOtpChanged;
  final bool autofocus;

  bool get _hasLegacyDescription {
    final lead = descriptionLead.trim();
    final target = maskedTarget?.trim() ?? '';
    return lead.isNotEmpty || target.isNotEmpty;
  }

  @override
  Widget build(BuildContext context) {
    final descriptionWidget = description ??
        (_hasLegacyDescription
            ? Text.rich(
                TextSpan(
                  style: GoogleFonts.inter(
                    fontSize: 15,
                    fontWeight: FontWeight.w400,
                    height: 22 / 15,
                    color: AppColors.textSecondary,
                  ),
                  children: [
                    TextSpan(text: descriptionLead),
                    if (maskedTarget != null && maskedTarget!.isNotEmpty)
                      TextSpan(
                        text: ' $maskedTarget',
                        style: GoogleFonts.inter(
                          fontSize: 15,
                          fontWeight: FontWeight.w600,
                          height: 22 / 15,
                          color: AppColors.textSecondary,
                        ),
                      ),
                  ],
                ),
              )
            : null);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        if (descriptionWidget != null) ...[
          Align(
            alignment: Alignment.centerLeft,
            child: descriptionWidget,
          ),
          const SizedBox(height: AppSpacing.pageDescriptionToFirstField),
        ],
        AppOtpInput(
          key: ValueKey(otpGeneration),
          hasError: wrongCode,
          showErrorMessage: false,
          locked: locked,
          autofocus: autofocus,
          onChanged: onOtpChanged,
          onCompleted: onCompleted,
        ),
        const SizedBox(height: AppSpacing.lg),
        Align(
          alignment: Alignment.centerLeft,
          child: resendCountdown > 0
              ? Text(
                  'Renvoyer le code dans ${resendCountdown}s',
                  style: GoogleFonts.inter(
                    fontSize: 14,
                    color: AppColors.textSecondary,
                  ),
                )
              : TextButton(
                  onPressed: resendInProgress ? null : onResend,
                  style: TextButton.styleFrom(
                    padding: EdgeInsets.zero,
                    minimumSize: Size.zero,
                    tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                  ),
                  child: Text(
                    'Renvoyer le code',
                    style: GoogleFonts.inter(
                      fontSize: 15,
                      fontWeight: FontWeight.w600,
                      color: resendInProgress
                          ? AppColors.textSecondary
                          : AppColors.indigo,
                    ),
                  ),
                ),
        ),
      ],
    );
  }
}
