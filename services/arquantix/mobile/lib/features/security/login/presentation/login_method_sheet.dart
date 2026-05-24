import 'package:flutter/material.dart';

import '../../../../core/jank_trace.dart';
import '../../../../design_system/atoms/app_colors.dart';
import '../../../../design_system/atoms/app_spacing.dart';
import '../../../../design_system/atoms/app_typography.dart';
import '../../../../design_system/components/app_primary_button.dart';
import '../../../../design_system/components/floating_ds_sheet.dart';

/// Actions secondaires depuis l’écran téléphone (hiérarchie : mobile > e-mail > passkey).
enum LoginMethodSheetChoice {
  email,
  passkey,
  lostPhone,
}

/// Feuille « Autres options » — gabarit flottant (espacements pilotés dans un seul [Column]).
Future<LoginMethodSheetChoice?> showLoginMethodSheet(BuildContext context) {
  JankTrace.tap('login_method_sheet');
  return showFloatingDsSheet<LoginMethodSheetChoice>(
    context: context,
    title: 'Autres options',
    buildBody: (pop) => [
      Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
            child: Text(
              'Vous pouvez choisir une autre méthode de connexion parmi les '
              'options ci-dessous.',
              textAlign: TextAlign.center,
              style: AppTypography.paragraph.copyWith(
                color: AppColors.textSecondary,
                height: 1.4,
              ),
            ),
          ),
          const SizedBox(height: AppSpacing.s8),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
            child: AppPrimaryButton(
              label: 'Continuer avec l’e-mail',
              size: AppPrimaryButtonSize.medium,
              onPressed: () => pop(LoginMethodSheetChoice.email),
            ),
          ),
          const SizedBox(height: AppSpacing.s2),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
            child: AppPrimaryButton(
              label: 'Continuer avec une passkey',
              variant: AppPrimaryButtonVariant.secondary,
              size: AppPrimaryButtonSize.medium,
              onPressed: () => pop(LoginMethodSheetChoice.passkey),
            ),
          ),
          const SizedBox(height: AppSpacing.s2),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
            child: AppPrimaryButton(
              label: 'Je n’ai plus accès à mon numéro',
              variant: AppPrimaryButtonVariant.ghost,
              size: AppPrimaryButtonSize.medium,
              onPressed: () => pop(LoginMethodSheetChoice.lostPhone),
            ),
          ),
        ],
      ),
    ],
  );
}

/// Depuis l’écran OTP SMS : uniquement e-mail ou passkey.
enum LoginOtpFallbackChoice {
  email,
  passkey,
}

Future<LoginOtpFallbackChoice?> showLoginOtpFallbackSheet(BuildContext context) {
  return showFloatingDsSheet<LoginOtpFallbackChoice>(
    context: context,
    title: 'Autres options de connexion',
    buildBody: (pop) => [
      Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
            child: Text(
              'Choisissez une autre méthode de connexion parmi les options ci-dessous.',
              textAlign: TextAlign.center,
              style: AppTypography.paragraph.copyWith(
                color: AppColors.textSecondary,
                height: 1.4,
              ),
            ),
          ),
          const SizedBox(height: AppSpacing.s8),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
            child: AppPrimaryButton(
              label: 'Continuer avec l’e-mail',
              size: AppPrimaryButtonSize.medium,
              onPressed: () => pop(LoginOtpFallbackChoice.email),
            ),
          ),
          const SizedBox(height: AppSpacing.s2),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
            child: AppPrimaryButton(
              label: 'Utiliser une passkey',
              variant: AppPrimaryButtonVariant.secondary,
              size: AppPrimaryButtonSize.medium,
              onPressed: () => pop(LoginOtpFallbackChoice.passkey),
            ),
          ),
        ],
      ),
    ],
  );
}
