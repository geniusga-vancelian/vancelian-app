import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';

/// Option affichée dans la modale pièces jointes (icône, titre, sous-texte).
class ChatAttachmentOption {
  const ChatAttachmentOption({
    required this.title,
    required this.subtitle,
    required this.icon,
    this.onTap,
  });
  final String title;
  final String subtitle;
  final IconData icon;
  final VoidCallback? onTap;
}

/// Modale type ChatGPT : ouverture par le "+", photos en haut, liste d’options en dessous.
class ChatAttachmentModal extends StatelessWidget {
  const ChatAttachmentModal({
    super.key,
    this.title = 'Assistant',
    this.photosLinkLabel = 'Toutes les photos',
    this.onPhotosLinkTap,
    this.options = const [],
  });

  final String title;
  final String photosLinkLabel;
  final VoidCallback? onPhotosLinkTap;
  final List<ChatAttachmentOption> options;

  /// Affiche la modale au-dessus du contexte.
  static Future<T?> show<T>(BuildContext context, {List<ChatAttachmentOption>? options}) {
    return showModalBottomSheet<T>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      barrierColor: Colors.black.withValues(alpha: 0.5),
      builder: (context) => ChatAttachmentModal(
        options: options ?? _defaultOptions(context),
      ),
    );
  }

  static List<ChatAttachmentOption> _defaultOptions(BuildContext context) {
    return [
      ChatAttachmentOption(
        title: 'Créer une image',
        subtitle: 'Transformez vos idées en images',
        icon: Icons.auto_awesome,
        onTap: () => Navigator.of(context).pop(),
      ),
      ChatAttachmentOption(
        title: 'Recherche approfondie',
        subtitle: 'Obtenir un rapport détaillé',
        icon: Icons.travel_explore,
        onTap: () => Navigator.of(context).pop(),
      ),
      ChatAttachmentOption(
        title: 'Recherche sur le Web',
        subtitle: 'Trouver des infos en temps réel',
        icon: Icons.language,
        onTap: () => Navigator.of(context).pop(),
      ),
      ChatAttachmentOption(
        title: 'Étudier et apprendre',
        subtitle: 'Apprendre un nouveau concept',
        icon: Icons.menu_book_outlined,
        onTap: () => Navigator.of(context).pop(),
      ),
      ChatAttachmentOption(
        title: 'Mode agent',
        subtitle: 'Tâches multi-étapes',
        icon: Icons.smart_toy_outlined,
        onTap: () => Navigator.of(context).pop(),
      ),
    ];
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        color: AppColors.cardBackground,
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      child: SafeArea(
        top: false,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Poignée
            Padding(
              padding: const EdgeInsets.only(top: AppSpacing.md),
              child: Center(
                child: Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: AppColors.placeholderIcon.withValues(alpha: 0.5),
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
            ),
            // En-tête : titre + lien photos
            Padding(
              padding: const EdgeInsets.fromLTRB(AppSpacing.lg, AppSpacing.lg, AppSpacing.lg, AppSpacing.sm),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    title,
                    style: AppTypography.sectionTitle.copyWith(color: AppColors.textPrimary),
                  ),
                  if (onPhotosLinkTap != null || photosLinkLabel.isNotEmpty)
                    Material(
                      color: Colors.transparent,
                      child: InkWell(
                        onTap: onPhotosLinkTap ?? () => Navigator.of(context).pop(),
                        borderRadius: BorderRadius.circular(4),
                        child: Padding(
                          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.sm, vertical: AppSpacing.xs),
                          child: Text(
                            photosLinkLabel,
                            style: AppTypography.bodyMedium.copyWith(
                              color: AppColors.accent,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ),
                      ),
                    ),
                ],
              ),
            ),
            // Bandeau photos : caméra + placeholders
            SizedBox(
              height: 80,
              child: ListView(
                scrollDirection: Axis.horizontal,
                padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg, vertical: AppSpacing.sm),
                children: [
                  _PhotoChip(icon: Icons.camera_alt_outlined, onTap: () => Navigator.of(context).pop()),
                  const SizedBox(width: AppSpacing.sm),
                  _PhotoChip(icon: Icons.photo_library_outlined, onTap: () => Navigator.of(context).pop()),
                  const SizedBox(width: AppSpacing.sm),
                  _PhotoChip(icon: Icons.photo_library_outlined, onTap: () => Navigator.of(context).pop()),
                ],
              ),
            ),
            const SizedBox(height: AppSpacing.sm),
            // Liste d’options
            ...options.map((opt) => _OptionTile(option: opt)),
            const SizedBox(height: AppSpacing.xxl),
          ],
        ),
      ),
    );
  }
}

class _PhotoChip extends StatelessWidget {
  const _PhotoChip({required this.icon, required this.onTap});

  final IconData icon;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Container(
          width: 72,
          height: 72,
          decoration: BoxDecoration(
            color: AppColors.chatInputBg,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: AppColors.placeholderIcon.withValues(alpha: 0.3)),
          ),
          child: Icon(icon, color: AppColors.textSecondary, size: 28),
        ),
      ),
    );
  }
}

class _OptionTile extends StatelessWidget {
  const _OptionTile({required this.option});

  final ChatAttachmentOption option;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: option.onTap ?? () => Navigator.of(context).pop(),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpacing.lg, vertical: AppSpacing.md),
          child: Row(
            children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: AppColors.chatInputBg,
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Icon(option.icon, color: AppColors.textPrimary, size: 22),
              ),
              const SizedBox(width: AppSpacing.lg),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      option.title,
                      style: AppTypography.titleSmall.copyWith(color: AppColors.textPrimary),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      option.subtitle,
                      style: AppTypography.meta.copyWith(color: AppColors.textSecondary),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
