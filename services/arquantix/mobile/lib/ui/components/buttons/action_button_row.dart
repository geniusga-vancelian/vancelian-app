import 'package:flutter/material.dart';

import 'button_rounded.dart';

/// Élément pour [ActionButtonRow] : icône, label, callback et variant.
class ActionButtonItem {
  const ActionButtonItem({
    required this.icon,
    required this.label,
    this.onTap,
    this.variant = ButtonRoundedVariant.secondary,
    this.size,
  });

  final IconData icon;
  final String label;
  final VoidCallback? onTap;
  final ButtonRoundedVariant variant;

  /// Custom size override. If null, uses [ButtonRounded] default (60).
  final double? size;
}

/// Module transparent avec marges (comme les autres modules), pas slidable.
/// Encapsule [ActionButtonRow] avec les mêmes marges que TransactionModule / WalletsModule.
class ActionButtonModule extends StatelessWidget {
  const ActionButtonModule({
    super.key,
    required this.child,
    this.horizontalPadding,
    this.topPadding,
    this.bottomPadding,
  });

  /// Contenu (en général [ActionButtonRow.defaultActions] ou [ActionButtonRow] avec [items]).
  final Widget child;
  /// Si non null, utilisé à la place de [_marginH] pour le padding horizontal (ex. 0 quand le parent applique déjà la marge).
  final double? horizontalPadding;
  /// Si non null, utilisé à la place de [_marginV] pour le padding au-dessus des boutons (ex. 0 pour coller au LineChart).
  final double? topPadding;
  /// Si non null, utilisé à la place de [_marginV] pour le padding en dessous des boutons.
  final double? bottomPadding;

  static const double _marginH = 16;
  static const double _marginV = 12;

  @override
  Widget build(BuildContext context) {
    final h = horizontalPadding ?? _marginH;
    final top = topPadding ?? _marginV;
    final bottom = bottomPadding ?? _marginV;
    return Padding(
      padding: EdgeInsets.only(left: h, right: h, top: top, bottom: bottom),
      child: child,
    );
  }
}

/// Ligne de boutons ronds type Revolut (ex. Déposer, Envoyer, Acheter, Plus).
/// Padding horizontal 16 ; répartition égale ; optionnellement [Wrap] sur petits écrans.
class ActionButtonRow extends StatelessWidget {
  /// Constructeur générique : liste d’[ActionButtonItem].
  const ActionButtonRow({
    super.key,
    required this.items,
    this.useWrap = false,
  })  : depositLabel = null,
        sendLabel = null,
        buyLabel = null,
        moreLabel = null,
        onDeposit = null,
        onSend = null,
        onBuy = null,
        onMore = null,
        heroStyle = false,
        heroLightStyle = false;

  /// Constructeur pratique pour les 4 actions par défaut (Déposer, Envoyer, Acheter, Plus).
  /// Si [heroStyle] est true : glass + icône/label blancs (header dark). Si [heroLightStyle] est true : glass + icône/label sombres (header light).
  const ActionButtonRow.defaultActions({
    super.key,
    this.depositLabel = 'Déposer',
    this.sendLabel = 'Envoyer',
    this.buyLabel = 'Acheter',
    this.moreLabel = 'Plus',
    this.onDeposit,
    this.onSend,
    this.onBuy,
    this.onMore,
    this.useWrap = false,
    this.heroStyle = false,
    this.heroLightStyle = false,
  }) : items = null;

  final List<ActionButtonItem>? items;

  /// Si true, utilise [Wrap] pour passer sur 2 lignes sur petits écrans.
  final bool useWrap;

  final String? depositLabel;
  final String? sendLabel;
  final String? buyLabel;
  final String? moreLabel;
  final VoidCallback? onDeposit;
  final VoidCallback? onSend;
  final VoidCallback? onBuy;
  final VoidCallback? onMore;

  /// Style hero (glass + icône/label blancs) pour header dark.
  final bool heroStyle;
  /// Style hero light (glass + icône/label sombres) pour header light.
  final bool heroLightStyle;

  /// Marge horizontale : 0 pour alignement avec le module (ActionButtonModule fournit déjà 16).
  static const double _horizontalPadding = 0;

  List<ActionButtonItem> _resolveItems() {
    if (items != null && items!.isNotEmpty) return items!;
    final ButtonRoundedVariant? v = heroLightStyle
        ? ButtonRoundedVariant.heroLight
        : (heroStyle ? ButtonRoundedVariant.hero : null);
    return [
      ActionButtonItem(
        icon: Icons.add,
        label: depositLabel ?? 'Déposer',
        onTap: onDeposit,
        variant: v ?? ButtonRoundedVariant.primary,
      ),
      ActionButtonItem(
        icon: Icons.arrow_forward_rounded,
        label: sendLabel ?? 'Envoyer',
        onTap: onSend,
        variant: v ?? ButtonRoundedVariant.secondary,
      ),
      ActionButtonItem(
        icon: Icons.swap_horiz_rounded,
        label: buyLabel ?? 'Acheter',
        onTap: onBuy,
        variant: v ?? ButtonRoundedVariant.secondary,
      ),
      ActionButtonItem(
        icon: Icons.more_horiz_rounded,
        label: moreLabel ?? 'Plus',
        onTap: onMore,
        variant: v ?? ButtonRoundedVariant.secondary,
      ),
    ];
  }

  @override
  Widget build(BuildContext context) {
    final resolved = _resolveItems();

    final buttons = resolved
        .map(
          (item) => ButtonRounded(
            icon: item.icon,
            label: item.label,
            onTap: item.onTap,
            variant: item.variant,
            size: item.size ?? 60,
            semanticLabel: item.label,
          ),
        )
        .toList();

    if (useWrap) {
      return Padding(
        padding: const EdgeInsets.symmetric(horizontal: _horizontalPadding),
        child: Wrap(
          alignment: WrapAlignment.spaceBetween,
          runSpacing: 24,
          children: buttons
              .map(
                (b) => SizedBox(
                  width: 60,
                  child: b,
                ),
              )
              .toList(),
        ),
      );
    }

    final alignment = buttons.length <= 3
        ? MainAxisAlignment.center
        : MainAxisAlignment.spaceBetween;
    final size = buttons.length <= 3
        ? MainAxisSize.min
        : MainAxisSize.max;

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: _horizontalPadding),
      child: Row(
        mainAxisAlignment: alignment,
        mainAxisSize: size,
        children: [
          for (int i = 0; i < buttons.length; i++) ...[
            buttons[i],
            if (i < buttons.length - 1 && buttons.length <= 3)
              const SizedBox(width: 24),
          ],
        ],
      ),
    );
  }
}
