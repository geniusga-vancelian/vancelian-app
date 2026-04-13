import 'package:flutter/material.dart';

import '../atoms/app_spacing.dart';
import 'app_section_title.dart';
import 'category_card.dart';

/// Élément d'une [CategoriesTab].
class CategoriesTabItem {
  final String imageUrl;
  final String title;
  final String description;

  const CategoriesTabItem({
    required this.imageUrl,
    required this.title,
    required this.description,
  });
}

/// Peek visible pour la 4e carte (et suivantes).
const double _peekWidth = 28;

/// Marge horizontale générale (même que page normale / Marketing Cards).
const double _horizontalMargin = AppSpacing.xl;

/// Module "Categories tab" : titre avec marge, liste de carrés (3 visibles + bout du 4e), même délire que Marketing Cards.
class CategoriesTab extends StatelessWidget {
  /// Titre du module (avec padding gauche/droite).
  final String title;

  /// Liste des catégories.
  final List<CategoriesTabItem> items;

  /// Index de l'élément actif (tabulation).
  final int selectedIndex;

  /// Callback quand une catégorie est sélectionnée.
  final ValueChanged<int> onSelected;

  const CategoriesTab({
    required this.title,
    required this.items,
    required this.selectedIndex,
    required this.onSelected,
    super.key,
  });

  @override
  Widget build(BuildContext context) {
    final screenWidth = MediaQuery.sizeOf(context).width;
    const gap = AppSpacing.md;
    // Zone utile = écran - marges gauche/droite - peek 4e (comme Marketing Cards)
    final availableWidth = screenWidth - _horizontalMargin * 2 - _peekWidth;
    final itemWidth = (availableWidth - gap * 2) / 3;

    const double textBlockHeight = 52;
    final totalCardHeight = itemWidth + textBlockHeight;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      mainAxisSize: MainAxisSize.min,
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: _horizontalMargin),
          child: AppSectionTitle(title),
        ),
        const SizedBox(height: AppSpacing.md),
        SizedBox(
          height: totalCardHeight,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.symmetric(horizontal: _horizontalMargin),
            itemCount: items.length,
            separatorBuilder: (_, __) => const SizedBox(width: gap),
            itemBuilder: (context, index) {
              final item = items[index];
              return CategoryCard(
                imageUrl: item.imageUrl,
                title: item.title,
                description: item.description,
                selected: index == selectedIndex,
                onTap: () => onSelected(index),
                squareSize: itemWidth,
              );
            },
          ),
        ),
      ],
    );
  }
}
