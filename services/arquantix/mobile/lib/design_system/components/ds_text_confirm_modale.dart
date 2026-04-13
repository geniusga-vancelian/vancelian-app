import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';
import 'app_primary_button.dart';
import 'sheet_title_bar.dart';

/// Modale de confirmation texte — alignée sur les feuilles DS ([SheetTitleBar] + [AppPrimaryButton]).
///
/// Barre supérieure type « navbar » feuille : titre centré, fermeture à gauche (équivalent Annuler).
/// Corps + deux boutons pill (secondaire gris puis action principale marque), comme [Modale] / vitrine DS.
class DsTextConfirmModale {
  DsTextConfirmModale._();

  /// Affiche la modale. Retourne `true` si l’action principale est choisie,
  /// `false` si annulation ou fermeture (barrière, croix, Annuler).
  static Future<bool?> show(
    BuildContext context, {
    required String title,
    required String message,
    String cancelLabel = 'Annuler',
    String confirmLabel = 'Confirmer',
    /// Au-dessus du shell (onglets) et des routes empilées.
    bool useRootNavigator = true,
  }) {
    return showDialog<bool>(
      context: context,
      useRootNavigator: useRootNavigator,
      barrierDismissible: true,
      barrierColor: Colors.black.withValues(alpha: 0.5),
      builder: (ctx) {
        return Dialog(
          insetPadding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.xl,
            vertical: AppSpacing.xxl,
          ),
          backgroundColor: Colors.transparent,
          elevation: 0,
          child: Material(
            color: AppColors.cardBackground,
            borderRadius: BorderRadius.circular(32),
            clipBehavior: Clip.antiAlias,
            child: Padding(
              padding: const EdgeInsets.only(bottom: AppSpacing.s10),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  SheetTitleBar(
                    title: title,
                    leadingButton: SheetCircleButton.leading(
                      onTap: () => Navigator.pop(ctx, false),
                    ),
                  ),
                  const SizedBox(height: AppSpacing.s6),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg),
                    child: Text(
                      message,
                      style: AppTypography.paragraph.copyWith(
                        color: AppColors.textSecondary,
                        height: 1.4,
                      ),
                    ),
                  ),
                  const SizedBox(height: AppSpacing.s6),
                  Center(
                    child: FractionallySizedBox(
                      widthFactor: 0.75,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          AppPrimaryButton(
                            label: cancelLabel,
                            variant: AppPrimaryButtonVariant.gray,
                            shrinkWrap: true,
                            onPressed: () => Navigator.pop(ctx, false),
                          ),
                          const SizedBox(height: AppSpacing.md),
                          AppPrimaryButton(
                            label: confirmLabel,
                            variant: AppPrimaryButtonVariant.primary,
                            shrinkWrap: true,
                            onPressed: () => Navigator.pop(ctx, true),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}
