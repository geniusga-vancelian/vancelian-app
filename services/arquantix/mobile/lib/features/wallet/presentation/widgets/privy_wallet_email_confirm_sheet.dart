import 'package:flutter/material.dart';

import '../../../../design_system/atoms/app_colors.dart';
import '../../../../design_system/atoms/app_spacing.dart';
import '../../../../design_system/atoms/app_typography.dart';
import '../../../../design_system/atoms/kalai_icons.dart';
import '../../../../design_system/components/app_primary_button.dart';
import '../../../../design_system/components/floating_ds_sheet.dart';
import '../../../../design_system/components/kalai_icon.dart';

/// Feuille DS (depuis le bas) : confirmer que l’e-mail profil est bien celui pour le code Privy.
///
/// L’adresse e-mail est affichée **en clair** directement dans la phrase de
/// confirmation (mise en valeur en gras) — pas de second bloc en dessous.
///
/// Retourne `true` si l’utilisateur confirme, `false` s’il indique que ce n’est pas le bon e-mail,
/// `null` si fermeture par croix / backdrop.
Future<bool?> showPrivyWalletEmailConfirmSheet({
  required BuildContext context,
  required String email,
}) {
  final emailDisplay = email.trim();
  return showFloatingDsSheet<bool>(
    context: context,
    title: 'Confirmer votre e-mail',
    // On expose **un seul enfant** au [BottomSheetContainer] afin de neutraliser
    // son écart automatique (24 px entre enfants directs) et de piloter
    // précisément les écarts internes : 32 px entre description et premier bouton,
    // 8 px entre les deux boutons.
    buildBody: (pop) => [
      Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
            child: RichText(
              textAlign: TextAlign.center,
              text: TextSpan(
                style: AppTypography.paragraph.copyWith(
                  color: AppColors.textSecondary,
                  height: 1.4,
                ),
                children: [
                  const TextSpan(
                    text:
                        'Pouvez-vous confirmer que votre adresse e-mail ',
                  ),
                  TextSpan(
                    text: emailDisplay,
                    style: AppTypography.paragraph.copyWith(
                      color: AppColors.textPrimary,
                      fontWeight: FontWeight.w600,
                      height: 1.4,
                    ),
                  ),
                  const TextSpan(
                    text:
                        ' est correcte ? Nous y enverrons un code de confirmation à 6 chiffres pour finaliser la création de votre wallet Privy.',
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: AppSpacing.s8),
          FractionallySizedBox(
            widthFactor: 0.75,
            child: AppPrimaryButton(
              label: 'Oui, je confirme',
              shrinkWrap: true,
              onPressed: () => pop(true),
            ),
          ),
          const SizedBox(height: AppSpacing.s2),
          FractionallySizedBox(
            widthFactor: 0.75,
            child: AppPrimaryButton(
              label: 'Non, modifier mon e-mail',
              variant: AppPrimaryButtonVariant.ghost,
              foregroundColor: AppColors.black,
              shrinkWrap: true,
              trailing: const KalaiIcon(
                KalaiIcons.arrowRight,
                size: 16,
                color: AppColors.black,
              ),
              onPressed: () => pop(false),
            ),
          ),
        ],
      ),
    ],
  );
}
