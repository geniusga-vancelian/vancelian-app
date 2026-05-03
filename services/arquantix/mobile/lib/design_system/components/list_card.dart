import 'package:flutter/material.dart';

import '../atoms/atoms.dart';
import 'kalai_icon.dart';

// ═════════════════════════════════════════════════════════════════════════════
// IconContainer — conteneur d'icône partagé (SettingsListItem, modules d'aide…)
// ═════════════════════════════════════════════════════════════════════════════

/// Forme du conteneur d'icône.
///
/// - [IconContainerShape.roundedSquare] : carré arrondi (défaut Figma,
///   `borderRadius` configurable, par défaut 10).
/// - [IconContainerShape.circle] : disque parfait — la `borderRadius` est
///   ignorée, le conteneur est rendu via `BoxShape.circle`.
enum IconContainerShape { roundedSquare, circle }

/// Conteneur d'icône réutilisable du DS pour [SettingsListItem],
/// modules d'aide, etc.
///
/// Figma : 36×36 par défaut (`md`), fond `#E5E5EA`, padding 10.
/// La forme est configurable via [shape] : carré arrondi (défaut) ou disque.
class IconContainer extends StatelessWidget {
  const IconContainer({
    super.key,
    required this.child,
    this.size = IconContainerSize.md,
    this.backgroundColor,
    this.borderRadius = 10,
    this.shape = IconContainerShape.roundedSquare,
  });

  final Widget child;
  final IconContainerSize size;
  final Color? backgroundColor;

  /// Rayon des coins quand [shape] = [IconContainerShape.roundedSquare].
  /// Ignoré si [shape] = [IconContainerShape.circle].
  final double borderRadius;

  /// Forme générale du conteneur (carré arrondi par défaut, ou disque).
  final IconContainerShape shape;

  double get _dimension => switch (size) {
        IconContainerSize.sm => 28,
        IconContainerSize.md => 36,
        IconContainerSize.lg => 44,
      };

  @override
  Widget build(BuildContext context) {
    final isCircle = shape == IconContainerShape.circle;
    return Container(
      width: _dimension,
      height: _dimension,
      decoration: BoxDecoration(
        color: backgroundColor ?? const Color(0xFFE5E5EA),
        shape: isCircle ? BoxShape.circle : BoxShape.rectangle,
        borderRadius:
            isCircle ? null : BorderRadius.circular(borderRadius),
      ),
      alignment: Alignment.center,
      child: child,
    );
  }
}

enum IconContainerSize { sm, md, lg }

/// Small chevron-right indicator for list rows.
///
/// Figma: 12×12, stroke #AEAEB2.
class ChevronRight extends StatelessWidget {
  const ChevronRight({
    super.key,
    this.color = const Color(0xFFAEAEB2),
    this.size = 12,
  });

  final Color color;
  final double size;

  @override
  Widget build(BuildContext context) {
    return Icon(
      Icons.chevron_right_rounded,
      size: size + 4,
      color: color,
    );
  }
}

// ═════════════════════════════════════════════════════════════════════════════
// ListCard — layout aligné EXACTEMENT sur TransactionListCard
// ═════════════════════════════════════════════════════════════════════════════
//
// Spécifications partagées avec [TransactionListCard] :
//   • Avatar : 36×36, **cercle parfait** (BoxShape.circle), icône 20px
//   • Outer card : padding 2px (gap entre bord carte et highlight pressé),
//                  radius 16, ombre defaultShadowList
//   • Item row : padding 14h / 14v, radius pressed 16, accentLight au tap
//   • Gap avatar ↔ texte : 12px
//   • Titre : AppTypography.itemPrimary (Inter SemiBold 15 / lh 20 / -0.23)
//   • Description : 13 / lh 16 / w400 / -0.08, AppColors.textMuted
//
// Différence avec TransactionListCard : pas de colonne montant à droite,
// uniquement un chevron optionnel (KalaiIcons.chevronRight, 20px, textMuted).

/// Données pour un item de [ListCardModule] (ou de [ListCard] standalone).
///
/// Trois modes pour le leading :
///   1. Avatar par défaut (36×36 cercle, fond [avatarBackgroundColor]) via
///      [icon] (+ [iconColor]).
///   2. Widget custom via [leadingWidget] (ex. [CryptoAvatar], [IconContainer]
///      avec une forme particulière, etc.).
///   3. **Aucun avatar** : ne fournir ni [icon] ni [leadingWidget]. Le titre
///      occupe alors toute la largeur (utile pour les listes type Centre
///      d'aide : catégories, articles…).
class ListCardItem {
  const ListCardItem({
    this.icon,
    this.iconColor = const Color(0xFF8E8E93),
    this.avatarBackgroundColor = const Color(0xFFE5E5EA),
    this.leadingWidget,
    required this.title,
    this.description,
    this.titleMaxLines = 2,
    this.showChevron = true,
    this.onTap,
  });

  /// Icône Material rendue dans l'avatar circulaire 36×36 (mode défaut).
  /// `null` (et [leadingWidget] `null`) → ligne sans avatar.
  final IconData? icon;

  /// Couleur de l'icône (mode défaut). Ignoré si [leadingWidget] est fourni.
  final Color iconColor;

  /// Couleur de fond du cercle 36×36 (mode défaut). Ignoré si [leadingWidget]
  /// est fourni.
  final Color avatarBackgroundColor;

  /// Widget leading custom (remplace l'avatar par défaut). `null` → ligne
  /// sans avatar.
  final Widget? leadingWidget;

  /// Titre principal (Inter SemiBold 15/20, -0.23).
  final String title;

  /// Description optionnelle, affichée sous le titre (13/16, textMuted).
  final String? description;

  /// Nombre maximum de lignes du titre (défaut 2).
  final int titleMaxLines;

  /// Affiche le chevron à droite de la ligne.
  final bool showChevron;

  /// Callback de tap. Si non null, active l'état pressed (accentLight).
  final VoidCallback? onTap;
}

/// Module liste : groupe plusieurs [ListCardItem] dans **un seul container
/// blanc** (carte avec ombre + radius), à la manière de [TransactionListCard]
/// mais sans colonne montant à droite.
///
/// Utiliser [ListCard] pour une carte autonome (1 seul item).
class ListCardModule extends StatelessWidget {
  const ListCardModule({
    super.key,
    required this.items,
    this.showShadow = true,
    this.embedded = false,
    this.itemSpacing,
  });

  final List<ListCardItem> items;

  /// Affiche l'ombre [AppShadow.defaultShadowList] autour du container.
  final bool showShadow;

  /// Espacement vertical entre les items. `null` ou `0` = items collés
  /// (séparés uniquement par leur padding interne).
  final double? itemSpacing;

  /// Si `true`, rend uniquement la liste d'items sans le container externe.
  /// Utile pour intégrer dans une carte existante.
  final bool embedded;

  static const double _outerPadding = 2;
  static const double _borderRadius = 16;

  // Constantes alignées sur TransactionListCard.
  static const double _itemPadH = 14;
  static const double _itemPadV = 14;
  static const double _avatarSize = 36;
  static const double _avatarIconSize = 20;
  static const double _gap = 12;

  static const Color _pressedColor = AppColors.accentLight;
  static const double _pressedRadius = 16;

  @override
  Widget build(BuildContext context) {
    final gap = itemSpacing ?? 0.0;

    final content = Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        for (int i = 0; i < items.length; i++) ...[
          _ListCardItemRow(data: items[i]),
          if (i < items.length - 1 && gap > 0) SizedBox(height: gap),
        ],
      ],
    );

    if (embedded) return content;

    return Container(
      padding: const EdgeInsets.all(_outerPadding),
      decoration: BoxDecoration(
        color: AppColors.cardBackground,
        borderRadius: BorderRadius.circular(_borderRadius),
        boxShadow: showShadow ? AppShadow.defaultShadowList : null,
      ),
      child: content,
    );
  }
}

/// Carte standalone (1 item) avec icône, titre, description optionnelle et
/// chevron optionnel.
///
/// Layout strictement aligné sur [TransactionListCard] (cf. constantes de
/// [ListCardModule]) :
///   • Avatar rond 36×36, gap 12
///   • Padding row 14×14, radius 16
///   • Typo titre : [AppTypography.itemPrimary]
///   • Pas de contenu à droite hors chevron optionnel
///
/// Pour grouper plusieurs items dans une seule carte, utiliser
/// [ListCardModule].
class ListCard extends StatelessWidget {
  const ListCard({
    super.key,
    this.icon,
    this.iconColor = const Color(0xFF8E8E93),
    this.avatarBackgroundColor = const Color(0xFFE5E5EA),
    this.leadingWidget,
    required this.title,
    this.description,
    this.titleMaxLines = 2,
    this.showChevron = true,
    this.hasShadow = true,
    this.onTap,
  });

  final IconData? icon;
  final Color iconColor;
  final Color avatarBackgroundColor;
  final Widget? leadingWidget;
  final String title;
  final String? description;
  final int titleMaxLines;
  final bool showChevron;
  final bool hasShadow;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return ListCardModule(
      showShadow: hasShadow,
      items: [
        ListCardItem(
          icon: icon,
          iconColor: iconColor,
          avatarBackgroundColor: avatarBackgroundColor,
          leadingWidget: leadingWidget,
          title: title,
          description: description,
          titleMaxLines: titleMaxLines,
          showChevron: showChevron,
          onTap: onTap,
        ),
      ],
    );
  }
}

// ─────────────────────────────────────────────────────────────────────────────
// _ListCardItemRow — rendu d'une ligne avec pressed state
// ─────────────────────────────────────────────────────────────────────────────

class _ListCardItemRow extends StatefulWidget {
  const _ListCardItemRow({required this.data});

  final ListCardItem data;

  @override
  State<_ListCardItemRow> createState() => _ListCardItemRowState();
}

class _ListCardItemRowState extends State<_ListCardItemRow> {
  bool _isPressed = false;

  static const TextStyle _descriptionStyle = TextStyle(
    fontSize: 13,
    fontWeight: FontWeight.w400,
    letterSpacing: -0.08,
    height: 16 / 13,
    color: AppColors.textMuted,
  );

  @override
  Widget build(BuildContext context) {
    final item = widget.data;
    final hasTap = item.onTap != null;
    final hasDescription =
        item.description != null && item.description!.isNotEmpty;
    final leading = _buildLeading(item);
    final hasLeading = leading != null;

    final row = DecoratedBox(
      decoration: BoxDecoration(
        color: _isPressed ? ListCardModule._pressedColor : Colors.transparent,
        borderRadius: BorderRadius.circular(ListCardModule._pressedRadius),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: ListCardModule._itemPadH,
          vertical: ListCardModule._itemPadV,
        ),
        child: Row(
          // Centré verticalement : avec 1 ligne de titre (20px) sans
          // description, l'avatar (36px) reste aligné au milieu du texte ;
          // avec titre + description (20+16=36px), l'effet est identique à
          // un alignement `start`.
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            if (hasLeading) ...[
              leading,
              const SizedBox(width: ListCardModule._gap),
            ],
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    item.title,
                    style: AppTypography.itemPrimary
                        .copyWith(color: AppColors.textPrimary),
                    maxLines: item.titleMaxLines,
                    overflow: TextOverflow.ellipsis,
                  ),
                  if (hasDescription)
                    Text(
                      item.description!,
                      style: _descriptionStyle,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                ],
              ),
            ),
            if (item.showChevron) ...[
              const SizedBox(width: 8),
              const KalaiIcon(
                KalaiIcons.chevronRight,
                size: 20,
                color: AppColors.textMuted,
              ),
            ],
          ],
        ),
      ),
    );

    if (!hasTap) return row;

    return GestureDetector(
      onTapDown: (_) => setState(() => _isPressed = true),
      onTapUp: (_) {
        setState(() => _isPressed = false);
        item.onTap?.call();
      },
      onTapCancel: () => setState(() => _isPressed = false),
      behavior: HitTestBehavior.opaque,
      child: row,
    );
  }

  Widget? _buildLeading(ListCardItem item) {
    if (item.leadingWidget != null) return item.leadingWidget;
    if (item.icon == null) return null;
    return Container(
      width: ListCardModule._avatarSize,
      height: ListCardModule._avatarSize,
      decoration: BoxDecoration(
        color: item.avatarBackgroundColor,
        shape: BoxShape.circle,
      ),
      alignment: Alignment.center,
      child: Icon(
        item.icon,
        size: ListCardModule._avatarIconSize,
        color: item.iconColor,
      ),
    );
  }
}
