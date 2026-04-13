import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_radius.dart';

/// Variante sémantique de l'alerte inline.
enum AppAlertVariant { info, warning, error, success }

/// Message inline contextuel avec icône, titre et description.
///
/// Contrairement à [AppSnackbar] / [AppToast] qui sont des overlays,
/// [AppAlert] s'insère directement dans le flux de la page.
class AppAlert extends StatelessWidget {
  const AppAlert({
    super.key,
    this.title,
    this.description,
    this.variant = AppAlertVariant.info,
    this.icon,
    this.onDismiss,
  });

  final String? title;
  final String? description;
  final AppAlertVariant variant;
  final IconData? icon;
  final VoidCallback? onDismiss;

  Color get _bgColor => switch (variant) {
        AppAlertVariant.info => AppColors.semanticInfoLight,
        AppAlertVariant.warning => AppColors.semanticWarningLight,
        AppAlertVariant.error => AppColors.semanticDangerLight,
        AppAlertVariant.success => AppColors.semanticPositiveLight,
      };

  Color get _accentColor => switch (variant) {
        AppAlertVariant.info => AppColors.semanticInfo,
        AppAlertVariant.warning => AppColors.semanticWarning,
        AppAlertVariant.error => AppColors.semanticDanger,
        AppAlertVariant.success => AppColors.semanticPositive,
      };

  IconData get _defaultIcon => switch (variant) {
        AppAlertVariant.info => Icons.info_outline_rounded,
        AppAlertVariant.warning => Icons.warning_amber_rounded,
        AppAlertVariant.error => Icons.error_outline_rounded,
        AppAlertVariant.success => Icons.check_circle_outline_rounded,
      };

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: _bgColor,
        borderRadius: BorderRadius.circular(AppRadius.md),
        border: Border.all(
          color: _accentColor.withValues(alpha: 0.25),
        ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon ?? _defaultIcon, size: 20, color: _accentColor),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                if (title != null)
                  Text(
                    title!,
                    style: GoogleFonts.inter(
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                      height: 18 / 14,
                      color: AppColors.textPrimary,
                    ),
                  ),
                if (title != null && description != null)
                  const SizedBox(height: 2),
                if (description != null)
                  Text(
                    description!,
                    style: GoogleFonts.inter(
                      fontSize: 13,
                      fontWeight: FontWeight.w400,
                      height: 18 / 13,
                      color: AppColors.textSecondary,
                    ),
                  ),
              ],
            ),
          ),
          if (onDismiss != null)
            GestureDetector(
              onTap: onDismiss,
              child: Padding(
                padding: const EdgeInsets.only(left: 8),
                child: Icon(Icons.close_rounded,
                    size: 18, color: _accentColor),
              ),
            ),
        ],
      ),
    );
  }
}
