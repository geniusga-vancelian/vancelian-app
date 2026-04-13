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
    required this.descriptionLead,
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

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Align(
          alignment: Alignment.centerLeft,
          child: Text.rich(
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
          ),
        ),
        const SizedBox(height: AppSpacing.pageDescriptionToFirstField),
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
