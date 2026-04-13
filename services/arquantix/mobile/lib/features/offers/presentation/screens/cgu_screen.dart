import 'package:flutter/material.dart';

import '../../../../design_system/design_system.dart';
import '../../../wallet/widgets/dashboard_scroll_template.dart';

/// Page Conditions générales d'utilisation (CGU).
/// [anchor] : identifiant de section pour scroll automatique (ex. "conditions-generales", "investisseurs").
class CguScreen extends StatefulWidget {
  const CguScreen({
    super.key,
    this.anchor,
  });

  /// Ancre pour cibler une zone (scroll vers la section correspondante au premier frame).
  final String? anchor;

  @override
  State<CguScreen> createState() => _CguScreenState();
}

class _CguScreenState extends State<CguScreen> {
  final ScrollController _scrollController = ScrollController();
  final Map<String, GlobalKey> _sectionKeys = {};

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _scrollToAnchor());
  }

  void _scrollToAnchor() {
    final anchor = widget.anchor;
    if (anchor == null || anchor.isEmpty) return;
    final key = _sectionKeys[anchor];
    if (key?.currentContext == null) return;
    Scrollable.ensureVisible(
      key!.currentContext!,
      duration: const Duration(milliseconds: 400),
      curve: Curves.easeInOut,
      alignment: 0.2,
    );
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  GlobalKey _key(String id) {
    _sectionKeys[id] ??= GlobalKey();
    return _sectionKeys[id]!;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      body: CustomScrollView(
        controller: _scrollController,
        slivers: [
          SliverAppBar(
            backgroundColor: AppColors.pageBackground,
            elevation: 0,
            scrolledUnderElevation: 0,
            leading: IconButton(
              icon: const Icon(Icons.arrow_back_ios_new_rounded),
              onPressed: () => Navigator.of(context).pop(),
              color: AppColors.textPrimary,
            ),
            title: Text(
              'Conditions générales',
              style: AppTypography.sectionTitle.copyWith(
                color: AppColors.textPrimary,
              ),
            ),
            centerTitle: true,
          ),
          SliverPadding(
            padding: const EdgeInsets.symmetric(
              horizontal: DashboardLayoutConstants.moduleHorizontalMargin,
              vertical: AppSpacing.lg,
            ),
            sliver: SliverList(
              delegate: SliverChildListDelegate([
                _Section(
                  key: _key('conditions-generales'),
                  title: 'Conditions générales d\'utilisation',
                  body: 'Les présentes conditions régissent l\'utilisation de la plateforme Arquantix et des services d\'investissement proposés. En accédant à nos services, vous acceptez ces conditions.',
                ),
                const SizedBox(height: AppSpacing.xl),
                _Section(
                  key: _key('investisseurs'),
                  title: 'Éligibilité des investisseurs',
                  body: 'Les offres d\'investissement sont réservées aux investisseurs éligibles conformément à la réglementation en vigueur. Vous attestez de votre capacité à assumer les risques liés à ces investissements.',
                ),
                const SizedBox(height: AppSpacing.xl),
                _Section(
                  key: _key('engagements'),
                  title: 'Engagements et responsabilités',
                  body: 'Arquantix s\'engage à fournir les informations nécessaires à la prise de décision. L\'investisseur est seul responsable de ses choix d\'investissement.',
                ),
              ]),
            ),
          ),
        ],
      ),
    );
  }
}

class _Section extends StatelessWidget {
  const _Section({
    super.key,
    required this.title,
    required this.body,
  });

  final String title;
  final String body;

  @override
  Widget build(BuildContext context) {
    return Column(
      key: key,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          title,
          style: AppTypography.titleMedium.copyWith(
            color: AppColors.textPrimary,
            fontWeight: FontWeight.w700,
          ),
        ),
        const SizedBox(height: AppSpacing.sm),
        Text(
          body,
          style: AppTypography.bodyMedium.copyWith(
            color: AppColors.textSecondary,
            height: 1.4,
          ),
        ),
      ],
    );
  }
}
