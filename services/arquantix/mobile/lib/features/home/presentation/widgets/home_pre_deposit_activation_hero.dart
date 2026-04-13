import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../../../../core/config.dart';
import '../../../../design_system/atoms/app_spacing.dart';
import '../../../../design_system/atoms/app_typography.dart';
import '../../../../design_system/atoms/dashboard_header_gradient.dart';
import '../../../../design_system/components/app_primary_button.dart';
import '../../../../l10n/app_localizations.dart';

/// Fond hero : même dégradé 3 couleurs que le bandeau dashboard ([DashboardHeaderGradient]).
Widget activationPreDepositHeroBackground() {
  return Container(
    decoration: DashboardHeaderGradient.decoration,
  );
}

/// Image : **URL parcours** ([apiHeroImageUrl] → `activation_journey.hero_image_url`) ;
/// sinon [Config.activationHeaderHeroUrl] (média R2 / dart-define) ;
/// en dernier recours seulement, compte **PARTIAL** sans aucune URL : asset coffre embarqué.
/// Puis titre [AppTypography.headerPrimary], tagline [bodyRegular], CTA, **36 px** sous le bouton.
Widget activationPreDepositHeroActionsColumn({
  required BuildContext context,
  bool useRegistrationPartialVaultAsset = false,
  String? apiHeroImageUrl,
  String? ctaLabel,
  VoidCallback? onCtaPressed,
}) {
  final l10n = AppLocalizations.of(context);
  if (l10n == null) {
    return const SizedBox.shrink();
  }
  final subtitleText = l10n.activationPreDepositHeroTagline;
  final titleText = l10n.activationHeroHeadline;

  const imageHeight = 120.0;
  const vaultAssetPath = 'assets/images/registration_partial_vault_header.png';

  final apiRaw = apiHeroImageUrl?.trim() ?? '';
  final resolvedFromJourney =
      apiRaw.isNotEmpty ? (Config.resolveLogoUrl(apiRaw) ?? apiRaw) : '';
  final defaultR2 = Config.activationHeaderHeroUrl.trim();
  final imageUrl =
      resolvedFromJourney.isNotEmpty ? resolvedFromJourney : defaultR2;

  final Widget heroImage;
  if (imageUrl.isNotEmpty) {
    heroImage = CachedNetworkImage(
      imageUrl: imageUrl,
      height: imageHeight,
      fit: BoxFit.contain,
      fadeInDuration: const Duration(milliseconds: 200),
      placeholder: (_, __) => const SizedBox(height: imageHeight),
      errorWidget: (_, __, ___) => const SizedBox(height: imageHeight),
    );
  } else if (useRegistrationPartialVaultAsset) {
    heroImage = Image.asset(
      vaultAssetPath,
      height: imageHeight,
      fit: BoxFit.contain,
    );
  } else {
    heroImage = const SizedBox(height: imageHeight);
  }

  return Column(
    mainAxisSize: MainAxisSize.min,
    crossAxisAlignment: CrossAxisAlignment.center,
    children: [
      heroImage,
      const SizedBox(height: AppSpacing.md),
      Padding(
        padding: const EdgeInsets.symmetric(horizontal: AppSpacing.xs),
        child: Text(
          titleText,
          textAlign: TextAlign.center,
          style: AppTypography.headerPrimary.copyWith(
            color: Colors.white,
          ),
          maxLines: 3,
        ),
      ),
      const SizedBox(height: AppSpacing.sm),
      Padding(
        padding: const EdgeInsets.symmetric(horizontal: AppSpacing.sm),
        child: Text(
          subtitleText,
          textAlign: TextAlign.center,
          style: AppTypography.bodyRegular.copyWith(
            color: Colors.white.withValues(alpha: 0.88),
            height: 1.35,
          ),
          maxLines: 4,
        ),
      ),
      if (ctaLabel != null && ctaLabel.trim().isNotEmpty) ...[
        const SizedBox(height: 36),
        SizedBox(
          width: double.infinity,
          child: AppPrimaryButton(
            label: ctaLabel.trim(),
            onPressed: onCtaPressed,
            shrinkWrap: true,
          ),
        ),
      ],
      const SizedBox(height: 36),
    ],
  );
}
