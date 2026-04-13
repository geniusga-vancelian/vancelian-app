import 'package:flutter/material.dart';

import '../atoms/app_spacing.dart';
import 'category_card.dart';

/// Élément d'une [CategoryCarousel].
class CategoryCarouselItem {
  /// Clé de cache stable (ex. id catégorie) pour éviter rechargement image au changement d'onglet.
  final String? imageCacheKey;
  final String imageUrl;
  final String title;
  /// Description sous le titre. Optionnelle (pas affichée si null ou vide).
  final String? description;

  const CategoryCarouselItem({
    this.imageCacheKey,
    required this.imageUrl,
    required this.title,
    this.description,
  });
}

/// Peek visible pour la 4e carte (et suivantes).
const double _peekWidth = 28;

/// Module catégories : scroll horizontal plein écran. 3 carrés exactement + bout du 4e visible.
class CategoryCarousel extends StatelessWidget {
  /// Liste des catégories.
  final List<CategoryCarouselItem> items;

  /// Index de l'élément actif (tabulation).
  final int selectedIndex;

  /// Callback quand une catégorie est sélectionnée.
  final ValueChanged<int> onSelected;

  const CategoryCarousel({
    required this.items,
    required this.selectedIndex,
    required this.onSelected,
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    final screenWidth = MediaQuery.sizeOf(context).width;
    const gap = AppSpacing.md;
    const horizontalMargin = AppSpacing.xl;
    // Largeur utile = écran - marges design system gauche/droite - peek 4e
    final availableWidth =
        screenWidth - horizontalMargin * 2 - _peekWidth;
    final itemWidth = (availableWidth - gap * 2) / 3;

    const double textBlockHeight = 52;
    final totalCardHeight = itemWidth + textBlockHeight;

    return SizedBox(
      height: totalCardHeight,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: horizontalMargin),
        itemCount: items.length,
        separatorBuilder: (_, __) => const SizedBox(width: gap),
        itemBuilder: (context, index) {
          final item = items[index];
          return CategoryCard(
            key: ValueKey<String>(item.imageCacheKey ?? '${item.title}-$index'),
            imageUrl: item.imageUrl,
            imageCacheKey: item.imageCacheKey,
            title: item.title,
            description: item.description,
            selected: index == selectedIndex,
            onTap: () => onSelected(index),
            squareSize: itemWidth,
          );
        },
      ),
    );
  }
}
