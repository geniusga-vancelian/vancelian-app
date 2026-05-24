import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../../design_system/atoms/app_colors.dart';
import '../../../../design_system/atoms/app_spacing.dart';
import '../../../../design_system/atoms/app_typography.dart';
import '../../../../design_system/components/article_document_card.dart';
import '../../../../design_system/components/module_gain.dart';
import '../../../../design_system/layout/module_horizontal_margin.dart';
import '../../domain/vault_exclusive_offer_modules.dart';

/// Liste de documents Vault — une [ArticleDocumentCard] par document (DS),
/// comme sur la page Design system / bloc article `DOCUMENTS_LIST`.
class VaultDocumentsListModule extends StatelessWidget {
  const VaultDocumentsListModule({
    super.key,
    required this.data,
    this.showModuleTitle = true,
  });

  final VaultDocumentsListModuleData data;
  final bool showModuleTitle;

  Future<void> _openUrl(String url) async {
    final u = Uri.tryParse(url.trim());
    if (u == null) return;
    if (await canLaunchUrl(u)) {
      await launchUrl(u, mode: LaunchMode.externalApplication);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (data.items.isEmpty) {
      return const SizedBox.shrink();
    }

    final sub = data.subtitle.trim();
    final title = data.moduleTitle.trim();
    final desc = data.description.trim();
    final hasHeader = sub.isNotEmpty || title.isNotEmpty || desc.isNotEmpty;

    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: kModuleHorizontalMargin,
        vertical: AppSpacing.lg,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (hasHeader) ...[
            if (sub.isNotEmpty)
              Text(
                sub.toUpperCase(),
                style: AppTypography.itemSupporting.copyWith(
                  color: AppColors.gray,
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                  letterSpacing: 1.2,
                ),
              ),
            if (sub.isNotEmpty && title.isNotEmpty) const SizedBox(height: AppSpacing.sm),
            if (title.isNotEmpty && showModuleTitle)
              SectionHeaderRow(title: title),
            if (desc.isNotEmpty)
              Padding(
                padding: EdgeInsets.only(
                  top: title.isNotEmpty && showModuleTitle ? AppSpacing.s1 : 0,
                  bottom: AppSpacing.sm,
                ),
                child: Text(
                  desc,
                  style: AppTypography.bodyMedium.copyWith(
                    color: AppColors.black,
                    fontSize: 18,
                    height: 1.35,
                  ),
                ),
              ),
            /// Aligné sur [LocalisationModule] (titre → carte blanche) et
            /// [VideoBlockArticleModule] (`md - shadow` ≈ 4px), pas un double `md`.
            const SizedBox(height: AppSpacing.s1),
          ],
          for (var i = 0; i < data.items.length; i++) ...[
            if (i > 0) const SizedBox(height: AppSpacing.s2),
            _DocumentCard(
              item: data.items[i],
              onOpen: _openUrl,
            ),
          ],
        ],
      ),
    );
  }
}

class _DocumentCard extends StatelessWidget {
  const _DocumentCard({
    required this.item,
    required this.onOpen,
  });

  final VaultDocumentListItemData item;
  final Future<void> Function(String url) onOpen;

  @override
  Widget build(BuildContext context) {
    final title = item.displayName.trim().isEmpty ? 'Document' : item.displayName.trim();
    final date = item.dateLabel.trim();
    final ext = _extensionFromDisplayName(title);
    final String subtitle;
    if (date.isNotEmpty) {
      subtitle = date;
    } else if (ext != null && ext.isNotEmpty) {
      subtitle = ext.toUpperCase();
    } else {
      subtitle = 'Document';
    }

    return ArticleDocumentCard(
      title: title,
      subtitle: subtitle,
      fileIcon: _iconFromExtension(ext),
      onTap: item.downloadUrl.trim().isNotEmpty
          ? () => onOpen(item.downloadUrl)
          : null,
    );
  }
}

String? _extensionFromDisplayName(String displayName) {
  final dot = displayName.lastIndexOf('.');
  if (dot < 0 || dot >= displayName.length - 1) return null;
  return displayName.substring(dot + 1);
}

IconData? _iconFromExtension(String? extRaw) {
  if (extRaw == null || extRaw.isEmpty) return null;
  final ext = extRaw.toUpperCase();
  if (ext == 'PDF') return Icons.picture_as_pdf_rounded;
  if (const {'PNG', 'JPG', 'JPEG', 'GIF', 'WEBP', 'SVG', 'HEIC'}.contains(ext)) {
    return Icons.image_rounded;
  }
  if (const {'MP4', 'MOV', 'AVI', 'MKV', 'WEBM'}.contains(ext)) {
    return Icons.movie_rounded;
  }
  if (const {'MP3', 'WAV', 'AAC', 'M4A', 'OGG'}.contains(ext)) {
    return Icons.audiotrack_rounded;
  }
  if (const {'ZIP', 'RAR', '7Z', 'TAR', 'GZ'}.contains(ext)) {
    return Icons.folder_zip_rounded;
  }
  if (const {'CSV', 'XLS', 'XLSX', 'NUMBERS'}.contains(ext)) {
    return Icons.table_chart_rounded;
  }
  if (const {'DOC', 'DOCX', 'PAGES', 'TXT', 'RTF'}.contains(ext)) {
    return Icons.description_rounded;
  }
  if (const {'PPT', 'PPTX', 'KEY'}.contains(ext)) {
    return Icons.slideshow_rounded;
  }
  return Icons.insert_drive_file_rounded;
}
