import 'package:flutter/material.dart';

import '../../../../design_system/design_system.dart';

class HelpSearchBar extends StatefulWidget {
  const HelpSearchBar({
    super.key,
    required this.controller,
    this.focusNode,
    this.hintText = 'Obtenez de l\'aide',
    this.onChanged,
  });

  final TextEditingController controller;
  /// Si null, un [FocusNode] interne est créé et disposé avec ce widget.
  final FocusNode? focusNode;
  final String hintText;
  final ValueChanged<String>? onChanged;

  @override
  State<HelpSearchBar> createState() => _HelpSearchBarState();
}

class _HelpSearchBarState extends State<HelpSearchBar> {
  FocusNode? _ownedFocus;

  FocusNode get _effectiveFocus {
    if (widget.focusNode != null) return widget.focusNode!;
    return _ownedFocus ??= FocusNode();
  }

  @override
  void dispose() {
    _ownedFocus?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: () => _effectiveFocus.requestFocus(),
      child: Container(
        constraints: const BoxConstraints(minHeight: 48),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(999),
          boxShadow: [
            BoxShadow(
              color: AppColors.textPrimary.withValues(alpha: 0.08),
              blurRadius: 22,
              spreadRadius: 0,
              offset: const Offset(0, 8),
            ),
          ],
        ),
        child: Row(
          children: [
            const SizedBox(width: AppSpacing.md),
            const Icon(Icons.search_rounded, color: AppColors.textPrimary, size: 22),
            const SizedBox(width: AppSpacing.xs),
            Expanded(
              child: TextField(
                focusNode: _effectiveFocus,
                controller: widget.controller,
                onChanged: widget.onChanged,
                // Évite sur iOS le surlignage / sélection large liée à l’autocorrection
                // et aux suggestions pendant la frappe dans une recherche.
                autocorrect: false,
                enableSuggestions: false,
                smartDashesType: SmartDashesType.disabled,
                smartQuotesType: SmartQuotesType.disabled,
                spellCheckConfiguration: const SpellCheckConfiguration.disabled(),
                textInputAction: TextInputAction.search,
                decoration: InputDecoration.collapsed(
                  hintText: widget.hintText,
                  hintStyle: AppTypography.bodyMedium.copyWith(color: AppColors.textSecondary),
                ),
                style: AppTypography.bodyMedium.copyWith(color: AppColors.textPrimary),
              ),
            ),
            const SizedBox(width: AppSpacing.md),
          ],
        ),
      ),
    );
  }
}

/// État vide partagé pour les listes du Centre d'aide ("Aucun résultat").
class HelpEmptyResults extends StatelessWidget {
  const HelpEmptyResults({super.key, this.label = 'Aucun résultat'});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: AppSpacing.s10),
        child: Text(
          label,
          style: AppTypography.itemSupporting.copyWith(
            color: AppColors.textMuted,
          ),
        ),
      ),
    );
  }
}

/// Carte DS groupant des items de type chevron-link pour le centre d'aide.
///
/// Utilise [SettingsCard] + [SettingsListItem] du design system.
class HelpChevronCardList extends StatelessWidget {
  const HelpChevronCardList({
    super.key,
    required this.items,
  });

  final List<HelpChevronCardItem> items;

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) {
      return const HelpEmptyResults();
    }

    return SettingsCard(
      children: items
          .map(
            (item) => SettingsListItem(
              leading: item.customLeading ??
                  (item.leadingIcon != null
                      ? IconContainer(
                          size: IconContainerSize.md,
                          shape: IconContainerShape.circle,
                          backgroundColor:
                              item.leadingBackgroundColor ?? const Color(0xFFF1F5F9),
                          child: Icon(
                            item.leadingIcon,
                            size: 18,
                            color: item.leadingIconColor ?? AppColors.textPrimary,
                          ),
                        )
                      : null),
              title: item.title,
              titleMaxLines: null,
              showChevron: false,
              onTap: item.onTap,
            ),
          )
          .toList(),
    );
  }
}

class HelpChevronCardItem {
  const HelpChevronCardItem({
    required this.title,
    required this.onTap,
    this.customLeading,
    this.leadingIcon,
    this.leadingBackgroundColor,
    this.leadingIconColor,
  });

  final String title;
  final VoidCallback onTap;
  /// Si défini, remplace la construction depuis [leadingIcon].
  final Widget? customLeading;
  final IconData? leadingIcon;
  final Color? leadingBackgroundColor;
  final Color? leadingIconColor;
}
