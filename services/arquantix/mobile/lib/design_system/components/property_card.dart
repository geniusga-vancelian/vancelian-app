import 'package:flutter/material.dart';

import '../atoms/atoms.dart';
import 'app_back_button.dart';
import 'circle_button.dart';
import 'glass_badge.dart';

/// Carte immersive plein écran avec image de fond, overlay dégradé,
/// badges, titre, description et boutons d'action.
///
/// Figma reference: Frame2147238686
/// - px-[24] py-[60], content px-[16]
/// - Overlay: linear-gradient bottom 50%→100% black 60% + uniform black 30%
/// - Gaps: 4px (badges↔title↔desc), 12px (info↔actions), 10px (buttons)
class PropertyCard extends StatelessWidget {
  final String? backgroundImageUrl;
  final String title;
  final String description;
  final String category;
  final String rate;
  final VoidCallback? onInvest;
  final VoidCallback? onBrochure;
  final VoidCallback? onPhotos;
  final VoidCallback? onVideos;
  final VoidCallback? onBackPress;
  final VoidCallback? onMenuPress;

  const PropertyCard({
    super.key,
    this.backgroundImageUrl,
    required this.title,
    required this.description,
    this.category = 'Immobilier',
    this.rate = 'Rate 11.24%',
    this.onInvest,
    this.onBrochure,
    this.onPhotos,
    this.onVideos,
    this.onBackPress,
    this.onMenuPress,
  });

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        Positioned.fill(child: _buildBackground()),
        SafeArea(
          child: Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.s6,
              vertical: 60,
            ),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                _buildTopNav(),
                _buildMainContent(),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildBackground() {
    final hasImage =
        backgroundImageUrl != null && backgroundImageUrl!.isNotEmpty;

    return Stack(
      fit: StackFit.expand,
      children: [
        if (hasImage)
          Image.network(
            backgroundImageUrl!,
            fit: BoxFit.cover,
            errorBuilder: (_, __, ___) => Container(color: AppColors.gray6),
          )
        else
          Container(color: AppColors.gray6),
        Container(color: AppColors.black.withValues(alpha: 0.3)),
        Container(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: [
                Colors.transparent,
                AppColors.black.withValues(alpha: 0.6),
              ],
              stops: const [0.499, 1.0],
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildTopNav() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        AppBackButton(
          kalaiIcon: KalaiIcons.arrowLeft,
          variant: AppBackButtonVariant.glassDark,
          onPressed: onBackPress,
        ),
        AppBackButton(
          icon: Icons.more_horiz_rounded,
          variant: AppBackButtonVariant.glassDark,
          onPressed: onMenuPress,
        ),
      ],
    );
  }

  Widget _buildMainContent() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.s4),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Info block: badges + title + description — gap 4px
          Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  GlassBadge(text: category),
                  const SizedBox(width: AppSpacing.s1),
                  GlassBadge(text: rate),
                ],
              ),
              const SizedBox(height: AppSpacing.s1),
              Text(
                title,
                style: AppTypography.headerPrimary.copyWith(
                  color: AppColors.white,
                  letterSpacing: -0.4,
                ),
              ),
              const SizedBox(height: AppSpacing.s1),
              Text(
                description,
                textAlign: TextAlign.center,
                style: AppTypography.bodySmRegular.copyWith(
                  color: AppColors.white,
                ),
              ),
            ],
          ),

          const SizedBox(height: AppSpacing.s3),

          CircleButtonRow(
            items: [
              CircleButtonItem(
                icon: Icons.add_rounded,
                kalaiAsset: KalaiIcons.add,
                label: 'Investir',
                onTap: onInvest,
              ),
              CircleButtonItem(
                icon: Icons.description_outlined,
                kalaiAsset: KalaiIcons.file,
                label: 'Brochure',
                onTap: onBrochure,
              ),
              CircleButtonItem(
                icon: Icons.photo_library_outlined,
                kalaiAsset: KalaiIcons.photo,
                label: 'Photos',
                onTap: onPhotos,
              ),
              CircleButtonItem(
                icon: Icons.videocam_outlined,
                kalaiAsset: KalaiIcons.video,
                label: 'Vidéos',
                onTap: onVideos,
              ),
            ],
          ),
        ],
      ),
    );
  }
}
