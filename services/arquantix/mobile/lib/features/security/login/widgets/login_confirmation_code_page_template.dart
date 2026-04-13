import 'package:flutter/material.dart';

import '../../../../design_system/atoms/app_spacing.dart';
import '../../../../design_system/components/app_page_title.dart';

/// Gabarit titre + espacements pour les écrans **code de confirmation** (OTP SMS, e-mail).
///
/// Aligné sur [LoginOtpScreen] : marge haute [AppSpacing.md], titre, puis
/// [AppSpacing.sm] avant la description / le bloc OTP — pas [AppSpacing.xl].
class LoginConfirmationCodePageHeader extends StatelessWidget {
  const LoginConfirmationCodePageHeader({
    super.key,
    required this.title,
  });

  final String title;

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        const SizedBox(height: AppSpacing.md),
        AppPageTitle(title),
        const SizedBox(height: AppSpacing.sm),
      ],
    );
  }
}
