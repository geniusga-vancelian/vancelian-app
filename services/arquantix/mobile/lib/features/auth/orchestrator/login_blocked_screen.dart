import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../design_system/atoms/app_colors.dart';
import '../../../design_system/atoms/app_spacing.dart';
import '../../../design_system/components/app_top_nav_bar.dart';

/// Connexion indisponible (politique adaptative / compte).
class LoginBlockedScreen extends StatelessWidget {
  const LoginBlockedScreen({
    super.key,
    this.reasonCodes = const [],
  });

  final List<String> reasonCodes;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      appBar: AppTopNavBar(
        leadingType: AppTopNavBarLeading.back,
        onBackTap: () => Navigator.of(context).pop(false),
        backgroundColor: AppColors.pageBackground,
        useDashboardStyle: true,
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.pageEdge),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const SizedBox(height: AppSpacing.xl),
              Text(
                'Connexion momentanément indisponible',
                textAlign: TextAlign.center,
                style: GoogleFonts.inter(
                  fontSize: 22,
                  fontWeight: FontWeight.w700,
                  color: AppColors.textPrimary,
                ),
              ),
              const SizedBox(height: AppSpacing.md),
              Text(
                'Pour votre sécurité, cette connexion n’est pas possible pour l’instant. '
                'Réessayez plus tard ou contactez le support si le problème continue.',
                textAlign: TextAlign.center,
                style: GoogleFonts.inter(
                  fontSize: 15,
                  height: 1.4,
                  color: AppColors.textSecondary,
                ),
              ),
              if (reasonCodes.isNotEmpty) ...[
                const SizedBox(height: AppSpacing.lg),
                Text(
                  reasonCodes.take(5).join('\n'),
                  textAlign: TextAlign.center,
                  style: GoogleFonts.inter(
                    fontSize: 12,
                    color: AppColors.textSecondary,
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
