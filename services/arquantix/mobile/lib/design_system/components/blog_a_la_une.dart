import 'dart:math' as math;

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

/// Marge horizontale (même que Marketing Cards / page normale).
const double _horizontalMargin = AppSpacing.xl;

/// Padding vertical pour ne pas couper les ombres des cartes (top/bottom).
const double _shadowPaddingVertical = AppSpacing.sm;

/// Espace titre → carousel (réduit de _shadowPaddingVertical pour garder le même ordre de grandeur).
const double _titleToCarouselGap = AppSpacing.md - _shadowPaddingVertical;

/// Module "Blog A la une" : titre, carrousel une carte par swipe (comme les news).
/// Utilise [NewsCard] comme carte interne (Figma design system).
class BlogALaUne extends StatefulWidget {
  /// Titre du module (défaut "A la une").
  final String title;

  /// Liste des articles à la une (1 ou plus).
  final List<BlogALaUneItem> items;

  /// Si fourni, le titre devient cliquable avec un caret et appelle ce callback.
  final VoidCallback? onTitleTap;

  const BlogALaUne({
    this.title = 'A la une',
    required this.items,
    this.onTitleTap,
    super.key,
  });

  @override
  State<BlogALaUne> createState() => _BlogALaUneState();
}

class _BlogALaUneState extends State<BlogALaUne> {
  double? _measuredHeight;
  bool _measureScheduled = false;
  final GlobalKey _measureKey = GlobalKey();

  /// Une carte par swipe — pas de défilement horizontal continu.
  late final PageController _pageController = PageController(viewportFraction: 1);

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

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

    final bool singleCard = widget.items.length == 1;
    /// Largeur de la carte pour [Offstage] (alignée sur la 1re page du carrousel).
    final cardWidth = singleCard
        ? availableWidth
        : screenWidth - _horizontalMargin - gap / 2;

    final last = widget.items.length - 1;

    if (_measuredHeight == null && !_measureScheduled) {
      _measureScheduled = true;
      WidgetsBinding.instance.addPostFrameCallback((_) => _measureCardHeight());
    }

    final height = _measuredHeight;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
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
        SizedBox(height: _titleToCarouselGap),
        if (height != null && height > 0)
          SizedBox(
            height: math.max(height, _minCardHeight) +
                _shadowPaddingVertical,
            child: PageView.builder(
              controller: _pageController,
              padEnds: false,
              itemCount: widget.items.length,
              itemBuilder: (context, index) {
                final left =
                    index == 0 ? _horizontalMargin : gap / 2;
                final right =
                    index == last ? _horizontalMargin : gap / 2;
                return Padding(
                  padding: EdgeInsets.only(
                    left: left,
                    right: right,
                    top: _shadowPaddingVertical,
                  ),
                  child: _buildNewsCard(widget.items[index]),
                );
              },
            ),
          )
        else
          Offstage(
            child: SizedBox(
              key: _measureKey,
              width: cardWidth,
              child: _buildNewsCard(widget.items.first),
            ),
          ),
      ],
    );
  }

  /// Hauteur minimale basée sur la structure fixe de [NewsCard] (image 167 + espacement + texte).
  static const double _minCardHeight =
      167 + // image section (Figma)
      8 + // padding haut contenu (image → titre)
      66 + // title (3 lines × 22px)
      8 + // gap title → meta
      18 + // meta (temps de lecture)
      16; // padding bas contenu
}
