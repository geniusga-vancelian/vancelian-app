import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'form_selection_rows.dart';

/// Liste multi-select : module blanc, cases à gauche, tuiles **inset** (sélection / press).
class SelectableMultiList<T> extends StatelessWidget {
  const SelectableMultiList({
    super.key,
    required this.items,
    required this.selectedItems,
    required this.onToggle,
    required this.labelBuilder,
    this.encapsulateInCard = true,
  });

  final List<T> items;
  final Set<T> selectedItems;
  final void Function(T) onToggle;
  final String Function(T) labelBuilder;
  final bool encapsulateInCard;

  @override
  Widget build(BuildContext context) {
    final list = Padding(
      padding: const EdgeInsets.all(kSelectionModuleInnerPadding),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          for (var i = 0; i < items.length; i++) ...[
            if (i > 0) const SizedBox(height: kSelectionRowSpacing),
            FormCheckboxRow(
            label: labelBuilder(items[i]),
            checked: selectedItems.contains(items[i]),
            onToggle: () {
              onToggle(items[i]);
              Future.microtask(HapticFeedback.selectionClick);
            },
          ),
        ],
      ],
    ),
    );

    if (!encapsulateInCard) {
      return list;
    }

    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.06),
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(16),
        child: list,
      ),
    );
  }
}
