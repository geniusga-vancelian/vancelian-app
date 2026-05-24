import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';
import '../atoms/kalai_icons.dart';
import 'kalai_icon.dart';
import 'news_card.dart';

/// Élément pour [BlogALaUne].
class BlogALaUneItem {
  final String title;
  final String coverUrl;
  final int readingTime;

  /// Texte meta personnalisé (ex. date). Si renseigné, remplace "X Minutes".
  final String? metaText;

  /// Nom de l'auteur affiché a droite de la date dans la ligne meta.
  final String? authorName;
  final VoidCallback? onTap;

  /// Tag affiché sur l'image (ex. "Real Estate", "Crypto"), optionnel.
  final String? tag;

  /// Plusieurs tags (Figma News) — prioritaire sur [tag] si non vide.
  final List<NewsCardTag>? tags;

  const BlogALaUneItem({
    required this.title,
    required this.coverUrl,
    required this.readingTime,
    this.metaText,
    this.authorName,
    this.onTap,
    this.tag,
    this.tags,
  });
}

/// Nombre de cartes visibles (1,05 = 1 pleine + léger peek 2e),
/// comme [ExclusiveOffersCarousel].
const double _visibleCardsCount = 1.05;

/// Marge horizontale (même que Marketing Cards / offres exclusives).
const double _horizontalMargin = AppSpacing.xl;

/// Padding vertical pour ne pas couper les ombres des cartes (top/bottom).
const double _shadowPaddingVertical = AppSpacing.sm;

/// Espace titre → carousel (réduit de _shadowPaddingVertical pour garder le même ordre de grandeur).
const double _titleToCarouselGap = AppSpacing.md - _shadowPaddingVertical;

/// Module « Blog à la une » : scroll horizontal continu + peek carte suivante,
/// même logique que [ExclusiveOffersCarousel] (page Invest).
///
/// Carte interne : [NewsCard] (Figma design system).
class BlogALaUne extends StatefulWidget {
  /// Titre du module (défaut "A la une").
  final String title;

  /// Liste des articles à la une (1 ou plus).
  final List<BlogALaUneItem> items;

  /// Si fourni, le titre devient cliquable avec un caret et appelle ce callback.
  final VoidCallback? onTitleTap;

  /// Affiche le titre + son gap. Permet aux écrans qui placent le module
  /// **en première position** de masquer le titre (cf. exclusive offer detail).
  final bool showTitle;

  const BlogALaUne({
    this.title = 'A la une',
    required this.items,
    this.onTitleTap,
    this.showTitle = true,
    super.key,
  });

  @override
  State<BlogALaUne> createState() => _BlogALaUneState();
}

class _BlogALaUneState extends State<BlogALaUne> {
  double? _measuredHeight;
  bool _measureScheduled = false;
  final GlobalKey _measureKey = GlobalKey();

  void _measureCardHeight() {
    final box = _measureKey.currentContext?.findRenderObject() as RenderBox?;
    if (box == null || !box.hasSize || !mounted) return;
    setState(() => _measuredHeight = box.size.height);
  }

  Widget _buildNewsCard(BlogALaUneItem item, {Key? key}) {
    return NewsCard(
      key: key,
      imageUrl: item.coverUrl,
      title: item.title,
      readTimeMinutes: item.readingTime,
      metaText: item.metaText,
      authorName: item.authorName,
      tags: item.tags,
      badgeLabel: item.tag,
      onTap: item.onTap,
    );
  }

  @override
  Widget build(BuildContext context) {
    if (widget.items.isEmpty) return const SizedBox.shrink();

    final screenWidth = MediaQuery.sizeOf(context).width;
    const gap = AppSpacing.md;
    final availableWidth = screenWidth - _horizontalMargin * 2;
    final cardWidth = (availableWidth - gap) / _visibleCardsCount;

    if (_measuredHeight == null && !_measureScheduled) {
      _measureScheduled = true;
      WidgetsBinding.instance.addPostFrameCallback((_) => _measureCardHeight());
    }

    final firstItem = widget.items.first;
    final height = _measuredHeight;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        if (widget.showTitle) ...[
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: _horizontalMargin),
            child: widget.onTitleTap != null
                ? Material(
                    color: Colors.transparent,
                    child: InkWell(
                      onTap: widget.onTitleTap,
                      borderRadius: BorderRadius.circular(4),
                      child: Padding(
                        padding: const EdgeInsets.symmetric(vertical: 2),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(
                              widget.title,
                              style: AppTypography.sectionTitle.copyWith(
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            const SizedBox(width: AppSpacing.xs),
                            const KalaiIcon(
                              KalaiIcons.chevronRight,
                              size: 22,
                              color: AppColors.textPrimary,
                            ),
                          ],
                        ),
                      ),
                    ),
                  )
                : Text(
                    widget.title,
                    style: AppTypography.sectionTitle.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
                  ),
          ),
          const SizedBox(height: _titleToCarouselGap),
        ],
        if (height != null && height > 0)
          SizedBox(
            height: height + _shadowPaddingVertical,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.only(
                left: _horizontalMargin,
                right: _horizontalMargin,
                top: _shadowPaddingVertical,
              ),
              itemCount: widget.items.length,
              separatorBuilder: (_, __) => const SizedBox(width: gap),
              itemBuilder: (context, index) {
                final item = widget.items[index];
                return SizedBox(
                  key: ValueKey<String>(
                      item.coverUrl.isNotEmpty ? item.coverUrl : 'blog-featured-$index'),
                  width: cardWidth,
                  child: _buildNewsCard(item),
                );
              },
            ),
          )
        else
          Offstage(
            child: SizedBox(
              key: _measureKey,
              width: cardWidth,
              child: _buildNewsCard(firstItem),
            ),
          ),
      ],
    );
  }
}
