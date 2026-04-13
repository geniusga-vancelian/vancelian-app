import 'package:flutter/material.dart';

import '../atoms/atoms.dart';

/// Ligne auteur : avatar circulaire + nom + date.
///
/// Figma: avatar 36px circle, nom 15px/w600, date 13px/w500 #8E8E93.
/// Fond blanc, padding 16, pleine largeur.
class ArticleAuthorRow extends StatelessWidget {
  final String name;
  final String? subtitle;
  final String? imageUrl;
  final Widget? avatar;

  const ArticleAuthorRow({
    super.key,
    required this.name,
    this.subtitle,
    this.imageUrl,
    this.avatar,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(AppSpacing.s4),
      decoration: BoxDecoration(
        color: AppColors.white,
        borderRadius: BorderRadius.circular(AppRadius.lg),
      ),
      child: Row(
        children: [
          _buildAvatar(),
          const SizedBox(width: AppSpacing.s3),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  name,
                  style: AppTypography.itemPrimary.copyWith(
                    color: AppColors.black,
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                ),
                if (subtitle != null)
                  Text(
                    subtitle!,
                    style: AppTypography.itemSupporting.copyWith(
                      color: AppColors.gray,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAvatar() {
    if (avatar != null) return avatar!;

    if (imageUrl != null && imageUrl!.isNotEmpty) {
      return ClipOval(
        child: SizedBox(
          width: 36,
          height: 36,
          child: Image.network(
            imageUrl!,
            fit: BoxFit.cover,
            errorBuilder: (_, __, ___) => _placeholderAvatar(),
          ),
        ),
      );
    }

    return _placeholderAvatar();
  }

  Widget _placeholderAvatar() {
    return Container(
      width: 36,
      height: 36,
      decoration: const BoxDecoration(
        color: Color(0xFFE5E5EA),
        shape: BoxShape.circle,
      ),
      alignment: Alignment.center,
      child: const Icon(Icons.person_rounded, size: 20, color: AppColors.gray),
    );
  }
}
