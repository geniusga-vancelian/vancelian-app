import 'package:flutter/material.dart';

import '../../../../design_system/design_system.dart';
import '../../../wallet/widgets/dashboard_scroll_template.dart';

/// Sous-page depuis le détail d'une offre : liste de documents téléchargeables.
class OfferDocumentsScreen extends StatelessWidget {
  const OfferDocumentsScreen({
    super.key,
    required this.projectTitle,
  });

  final String projectTitle;

  /// Documents mockés ; à remplacer par un appel API par projet.
  static List<({String label, String? url})> _mockDocuments() {
    return [
      (label: 'Note d\'information', url: null),
      (label: 'Brochure projet', url: null),
      (label: 'Règlement', url: null),
    ];
  }

  @override
  Widget build(BuildContext context) {
    final documents = _mockDocuments();
    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      appBar: AppBar(
        backgroundColor: AppColors.pageBackground,
        elevation: 0,
        scrolledUnderElevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new_rounded),
          onPressed: () => Navigator.of(context).pop(),
          color: AppColors.textPrimary,
        ),
        title: Text(
          'Documents',
          style: AppTypography.sectionTitle.copyWith(
            color: AppColors.textPrimary,
          ),
        ),
        centerTitle: true,
      ),
      body: ListView(
        padding: const EdgeInsets.symmetric(
          horizontal: DashboardLayoutConstants.moduleHorizontalMargin,
          vertical: AppSpacing.lg,
        ),
        children: [
          Text(
            projectTitle,
            style: AppTypography.title2.copyWith(
              color: AppColors.textSecondary,
            ),
          ),
          const SizedBox(height: AppSpacing.lg),
          ...documents.map((doc) => _DocumentTile(
                label: doc.label,
                onTap: doc.url != null
                    ? () => _openDocument(context, doc.url!)
                    : () => _onDownloadTap(context, doc.label),
              )),
        ],
      ),
    );
  }

  void _openDocument(BuildContext context, String url) {
    // TODO: ouvrir URL ou télécharger via url_launcher / package download
  }

  void _onDownloadTap(BuildContext context, String label) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Téléchargement de « $label » (à brancher)'),
        behavior: SnackBarBehavior.floating,
      ),
    );
  }
}

class _DocumentTile extends StatelessWidget {
  const _DocumentTile({
    required this.label,
    required this.onTap,
  });

  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpacing.sm),
      child: Material(
        color: AppColors.cardBackground,
        borderRadius: BorderRadius.circular(12),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(12),
          child: Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: AppSpacing.lg,
              vertical: AppSpacing.md,
            ),
            child: Row(
              children: [
                Icon(
                  Icons.description_outlined,
                  color: AppColors.textPrimary,
                  size: 24,
                ),
                const SizedBox(width: AppSpacing.md),
                Expanded(
                  child: Text(
                    label,
                    style: AppTypography.bodyMedium.copyWith(
                      color: AppColors.textPrimary,
                    ),
                  ),
                ),
                Icon(
                  Icons.download_rounded,
                  color: AppColors.accent,
                  size: 22,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
