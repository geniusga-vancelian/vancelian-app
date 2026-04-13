import 'package:flutter/material.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';
import 'app_section_title.dart';
import 'news_row_card.dart';

/// Élément pour [BlogNews].
class BlogNewsItem {
  final String title;
  final String coverUrl;
  final int readingTime;
  final VoidCallback? onTap;

  const BlogNewsItem({
    required this.title,
    required this.coverUrl,
    required this.readingTime,
    this.onTap,
  });
}

/// Nombre de cartes visibles quand plusieurs articles (1,05 = 1 pleine + 5 % de la 2e).
const double _visibleCardsCount = 1.05;

/// Marge horizontale (même que BlogALaUne / Marketing Cards).
const double _horizontalMargin = AppSpacing.xl;

/// Hauteur minimale de la zone de tap du titre (recommandation accessibilité ~44 pt).
const double _titleTapMinHeight = 44;

/// Module "Blog News" : même logique que BlogALaUne (titre, sliding, marges) avec cartes article en ligne (NewsRowCard).
class BlogNews extends StatefulWidget {
  /// Titre du module (ex. "All news").
  final String title;

  /// Liste des articles.
  final List<BlogNewsItem> items;

  /// Si fourni, le titre devient cliquable avec un caret (redirection ex. vers la page blog).
  final VoidCallback? onTitleTap;

  /// Afficher l'image dans chaque carte (défaut true). Si false, le contenu occupe toute la place.
  final bool withImage;

  const BlogNews({
    required this.title,
    required this.items,
    this.onTitleTap,
    this.withImage = true,
    super.key,
  });

  @override
  State<BlogNews> createState() => _BlogNewsState();
}

class _BlogNewsState extends State<BlogNews> {
  double? _measuredHeight;
  bool _measureScheduled = false;
  final GlobalKey _measureKey = GlobalKey();

  void _measureCardHeight() {
    final box = _measureKey.currentContext?.findRenderObject() as RenderBox?;
    if (box == null || !box.hasSize || !mounted) return;
    setState(() => _measuredHeight = box.size.height);
  }

  Widget _buildTitleTapZone({required Widget child}) => child;

  @override
  Widget build(BuildContext context) {
    if (widget.items.isEmpty) return const SizedBox.shrink();

    final screenWidth = MediaQuery.sizeOf(context).width;
    const gap = AppSpacing.md;
    final availableWidth = screenWidth - _horizontalMargin * 2;

    final bool singleCard = widget.items.length == 1;
    final cardWidth = singleCard ? availableWidth : (availableWidth - gap) / _visibleCardsCount;

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
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: _horizontalMargin),
          child: widget.onTitleTap != null
              ? _buildTitleTapZone(
                  child: Semantics(
                    button: true,
                    label: widget.title,
                    hint: 'Ouvrir la section Flash info',
                    child: Material(
                      color: Colors.transparent,
                      child: InkWell(
                        onTap: widget.onTitleTap,
                        borderRadius: BorderRadius.circular(4),
                        child: ConstrainedBox(
                          constraints: const BoxConstraints(
                            minHeight: _titleTapMinHeight,
                            minWidth: double.infinity,
                          ),
                          child: Padding(
                            padding: const EdgeInsets.symmetric(vertical: 8),
                            child: SizedBox(
                              width: double.infinity,
                              child: Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Text(widget.title, style: AppTypography.sectionTitle),
                                  const SizedBox(width: AppSpacing.xs),
                                  Icon(
                                    Icons.chevron_right,
                                    size: 22,
                                    color: AppColors.textPrimary,
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),
                  ),
                )
              : AppSectionTitle(widget.title),
        ),
        const SizedBox(height: AppSpacing.md),
        if (height != null && height > 0)
          SizedBox(
            height: height,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: _horizontalMargin),
              itemCount: widget.items.length,
              separatorBuilder: (_, __) => const SizedBox(width: gap),
              itemBuilder: (context, index) {
                final item = widget.items[index];
                return SizedBox(
                  width: cardWidth,
                  child: NewsRowCard(
                    title: item.title,
                    coverUrl: item.coverUrl,
                    readingTime: item.readingTime,
                    onTap: item.onTap ?? () {},
                    showImage: widget.withImage,
                  ),
                );
              },
            ),
          )
        else
          Offstage(
            child: SizedBox(
              key: _measureKey,
              width: cardWidth,
              child: NewsRowCard(
                title: firstItem.title,
                coverUrl: firstItem.coverUrl,
                readingTime: firstItem.readingTime,
                onTap: firstItem.onTap ?? () {},
                showImage: widget.withImage,
              ),
            ),
          ),
      ],
    );
  }
}
