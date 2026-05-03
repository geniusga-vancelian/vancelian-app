import 'package:flutter/material.dart';

import '../../../../design_system/design_system.dart';

/// Barre de recherche du module Academy. Identique visuellement à
/// [HelpSearchBar] (DS partagé) mais hint adapté.
class AcademySearchBar extends StatefulWidget {
  const AcademySearchBar({
    super.key,
    required this.controller,
    this.hintText = 'Rechercher dans l\'Academy',
    this.onChanged,
  });

  final TextEditingController controller;
  final String hintText;
  final ValueChanged<String>? onChanged;

  @override
  State<AcademySearchBar> createState() => _AcademySearchBarState();
}

class _AcademySearchBarState extends State<AcademySearchBar> {
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

/// Liste à chevron pour Academy (collections / catégories / articles).
/// Forme et règles visuelles identiques à `HelpChevronCardList` (DS partagé).
class AcademyChevronCardList extends StatelessWidget {
  const AcademyChevronCardList({
    super.key,
    required this.items,
  });

  final List<AcademyChevronCardItem> items;

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
                      shape: IconContainerShape.circle,
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
              titleMaxLines: null,
              showChevron: false,
              onTap: item.onTap,
            ),
          )
          .toList(),
    );
  }
}

class AcademyChevronCardItem {
  const AcademyChevronCardItem({
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
