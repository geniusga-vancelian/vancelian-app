import 'package:flutter/material.dart';

import '../../../design_system/design_system.dart';
import 'dashboard_scroll_template.dart';

/// Template de page détail transaction : AppBar avec bouton Retour + titre optionnel + zone contenu.
class TransactionTemplate extends StatelessWidget {
  const TransactionTemplate({
    super.key,
    required this.child,
    this.title,
    this.onBack,
  });

  /// Contenu principal sous l'AppBar.
  final Widget child;

  /// Titre affiché dans l'AppBar. Si null, pas de titre.
  final String? title;

  /// Callback du bouton Retour. Si null, [Navigator.pop].
  final VoidCallback? onBack;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      appBar: AppTopNavBar(
        leadingType: AppTopNavBarLeading.back,
        title: title,
        onBackTap: onBack ?? () => Navigator.of(context).pop(),
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: DashboardLayoutConstants.moduleHorizontalMargin),
          child: child,
        ),
      ),
    );
  }
}
