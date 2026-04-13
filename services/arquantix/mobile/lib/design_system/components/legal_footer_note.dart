import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../atoms/app_colors.dart';
import '../atoms/app_spacing.dart';
import '../atoms/app_typography.dart';

/// Note de conformité bas de page. Affiche un texte discret avec liens
/// cliquables intégrés. Réutilisable pour toute surface nécessitant un
/// disclaimer juridique court.
///
/// Supporte des segments de texte (plain ou lien) via [LegalTextSegment].
class LegalFooterNote extends StatelessWidget {
  const LegalFooterNote({
    required this.segments,
    super.key,
    this.padding,
  });

  final List<LegalTextSegment> segments;
  final EdgeInsetsGeometry? padding;

  /// Construit depuis un JSON CMS.
  ///
  /// ```json
  /// {
  ///   "type": "legalFooterNote",
  ///   "segments": [
  ///     { "text": "En confirmant, vous acceptez les " },
  ///     { "text": "Conditions générales", "url": "https://..." }
  ///   ]
  /// }
  /// ```
  static LegalFooterNote? fromJson(dynamic json) {
    if (json is! Map<String, dynamic>) return null;
    if (json['type'] != 'legalFooterNote') return null;
    final segsRaw = json['segments'];
    if (segsRaw is! List || segsRaw.isEmpty) return null;
    final segs = <LegalTextSegment>[];
    for (final s in segsRaw) {
      if (s is! Map<String, dynamic>) continue;
      final text = s['text'] as String?;
      if (text == null || text.isEmpty) continue;
      segs.add(LegalTextSegment(text: text, url: s['url'] as String?));
    }
    if (segs.isEmpty) return null;
    return LegalFooterNote(segments: segs);
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: padding ??
          const EdgeInsets.symmetric(
            horizontal: AppSpacing.xs,
            vertical: AppSpacing.sm,
          ),
      child: Text.rich(
        TextSpan(
          children: segments.map((seg) {
            if (seg.url != null) {
              return TextSpan(
                text: seg.text,
                style: AppTypography.bodySmall.copyWith(
                  color: AppColors.indigo,
                  decoration: TextDecoration.underline,
                  decorationColor: AppColors.indigo.withValues(alpha: 0.4),
                  height: 1.5,
                  fontSize: 12,
                ),
                recognizer: TapGestureRecognizer()
                  ..onTap = () => _openUrl(seg.url!),
              );
            }
            return TextSpan(
              text: seg.text,
              style: AppTypography.bodySmall.copyWith(
                color: AppColors.textSecondary,
                height: 1.5,
                fontSize: 12,
              ),
            );
          }).toList(),
        ),
      ),
    );
  }

  Future<void> _openUrl(String url) async {
    final uri = Uri.tryParse(url);
    if (uri != null && await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }
}

/// Segment de texte pour [LegalFooterNote] : plain text ou lien.
class LegalTextSegment {
  const LegalTextSegment({required this.text, this.url});

  final String text;
  final String? url;
}
