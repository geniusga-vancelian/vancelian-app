import 'package:flutter/material.dart';

import '../../../../design_system/design_system.dart';

class HelpSearchBar extends StatefulWidget {
  const HelpSearchBar({
    super.key,
    required this.controller,
    this.hintText = 'Obtenez de l\'aide',
    this.onChanged,
  });

  final TextEditingController controller;
  final String hintText;
  final ValueChanged<String>? onChanged;

  @override
  State<HelpSearchBar> createState() => _HelpSearchBarState();
}

class _HelpSearchBarState extends State<HelpSearchBar> {
  late final FocusNode _focusNode;

  @override
  void initState() {
    super.initState();
    _focusNode = FocusNode();
  }

  @override
  void dispose() {
    _focusNode.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: () => _focusNode.requestFocus(),
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
                focusNode: _focusNode,
                controller: widget.controller,
                onChanged: widget.onChanged,
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
      return Center(
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: AppSpacing.s10),
          child: Text(
            'Aucun résultat',
            style: AppTypography.itemSupporting.copyWith(
              color: AppColors.textMuted,
            ),
          ),
        ),
      );
    }

    return SettingsCard(
      children: items
          .map(
            (item) => SettingsListItem(
              leading: item.leadingIcon != null
                  ? IconContainer(
                      size: IconContainerSize.md,
                      borderRadius: 10,
                      backgroundColor:
                          item.leadingBackgroundColor ?? const Color(0xFFF1F5F9),
                      child: Icon(
                        item.leadingIcon,
                        size: 18,
                        color: item.leadingIconColor ?? AppColors.textPrimary,
                      ),
                    )
                  : null,
              title: item.title,
              showChevron: true,
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
    this.leadingIcon,
    this.leadingBackgroundColor,
    this.leadingIconColor,
  });

  final String title;
  final VoidCallback onTap;
  final IconData? leadingIcon;
  final Color? leadingBackgroundColor;
  final Color? leadingIconColor;
}
