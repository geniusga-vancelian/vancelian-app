import 'package:flutter/material.dart';

import '../atoms/app_spacing.dart';
import '../layout/module_horizontal_margin.dart';
import 'localisation_card.dart';
import 'module_gain.dart';

/// Module « Localisation » : titre de section, carte embed Google Maps, adresse + complément.
///
/// Le rendu suit le design system ([SectionHeaderRow] + [LocalisationCard], fond page clair).
class LocalisationModule extends StatelessWidget {
  const LocalisationModule({
    super.key,
    required this.moduleTitle,
    required this.description,
    required this.embedUrl,
  });

  final String moduleTitle;
  final String description;
  final String embedUrl;

  /// Délègue à [LocalisationCard.isAllowedEmbedUrl] (rétrocompatibilité des call sites).
  static bool isAllowedEmbedUrl(String raw) => LocalisationCard.isAllowedEmbedUrl(raw);

  @override
  Widget build(BuildContext context) {
    final title = moduleTitle.trim();
    final desc = description.trim();
    final hasTitle = title.isNotEmpty;

    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: kModuleHorizontalMargin,
        vertical: AppSpacing.lg,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (hasTitle) SectionHeaderRow(title: title),
          if (hasTitle) const SizedBox(height: AppSpacing.s1),
          LocalisationCard(
            embedUrl: embedUrl,
            complement: desc,
          ),
        ],
      ),
    );
  }
}
