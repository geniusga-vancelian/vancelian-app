import 'package:flutter/material.dart';

import '../atoms/app_spacing.dart';

/// Rangée de CTA du hero détail instrument : largeur calculée **comme s’il y avait deux boutons** ;
/// chaque emplacement est **&lt; 50 %** de la largeur utile (marges page déjà exclues du [LayoutBuilder]).
class InstrumentDetailHeroCtaRow extends StatelessWidget {
  const InstrumentDetailHeroCtaRow({
    super.key,
    required this.children,
  }) : assert(children.length <= 2);

  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    if (children.isEmpty) return const SizedBox.shrink();
    return LayoutBuilder(
      builder: (context, constraints) {
        final gap = AppSpacing.sm;
        final maxW = constraints.maxWidth;
        final slot = (maxW - gap) / 2;
        if (children.length == 1) {
          return Align(
            alignment: Alignment.centerLeft,
            child: SizedBox(width: slot, child: children.first),
          );
        }
        return Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            SizedBox(width: slot, child: children[0]),
            SizedBox(width: gap),
            SizedBox(width: slot, child: children[1]),
          ],
        );
      },
    );
  }
}
