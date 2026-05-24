import 'package:flutter/material.dart';

import 'lifi_swap_flow/lifi_swap_to_selection_screen.dart';

/// Point d'entrée swap LI.FI — flow multi-étapes (TO → FROM → montant → confirmation).
class LifiSwapScreen extends StatelessWidget {
  const LifiSwapScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const LifiSwapToSelectionScreen();
  }
}
