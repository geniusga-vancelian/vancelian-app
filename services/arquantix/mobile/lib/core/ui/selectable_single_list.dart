import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'form_selection_rows.dart';

/// Liste single-select : module blanc, radios à gauche, tuiles **inset** (sélection / press).
class SelectableSingleList<T> extends StatelessWidget {
  const SelectableSingleList({
    super.key,
    required this.items,
    required this.selected,
    required this.onSelect,
    required this.labelBuilder,
    this.encapsulateInCard = true,
  });

  final List<T> items;
  final T? selected;
  final void Function(T) onSelect;
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
            FormRadioRow(
            label: labelBuilder(items[i]),
            selected: selected == items[i],
            onSelect: () {
              onSelect(items[i]);
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
