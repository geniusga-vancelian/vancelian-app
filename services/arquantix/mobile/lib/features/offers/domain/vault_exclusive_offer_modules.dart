import 'vault_visualization_url.dart';

/// Ligne document résolue (équivalent `VaultDocumentsListResolvedItem` côté web).
class VaultDocumentListItemData {
  const VaultDocumentListItemData({
    required this.mediaId,
    required this.downloadUrl,
    required this.displayName,
    required this.dateLabel,
  });

  final String mediaId;
  final String downloadUrl;
  final String displayName;
  final String dateLabel;
}

/// Données [DocumentsListModule] du vault pour l’écran offre exclusive.
class VaultDocumentsListModuleData {
  const VaultDocumentsListModuleData({
    required this.subtitle,
    required this.moduleTitle,
    required this.description,
    required this.items,
  });

  final String subtitle;
  final String moduleTitle;
  final String description;
  final List<VaultDocumentListItemData> items;
}

/// Données [VirtualVisualizationModule] du vault.
class VaultVirtualVisualizationModuleData {
  const VaultVirtualVisualizationModuleData({
    required this.moduleTitle,
    required this.description,
    required this.normalizedUrl,
    required this.rawUrl,
  });

  final String moduleTitle;
  final String description;
  final String normalizedUrl;
  final String rawUrl;

  bool get canEmbed => isVirtualVisualizationEmbedUrl(normalizedUrl);

  bool get hasRenderableContent =>
      moduleTitle.trim().isNotEmpty ||
      description.trim().isNotEmpty ||
      canEmbed ||
      rawUrl.trim().isNotEmpty;
}

VaultDocumentsListModuleData? documentsListModuleFromVault(Map<String, dynamic>? vaultData) {
  if (vaultData == null) return null;
  final modules = vaultData['modules'];
  if (modules is! List) return null;
  for (final raw in modules) {
    if (raw is! Map) continue;
    final m = Map<String, dynamic>.from(raw);
    if (m['enabled'] == false) continue;
    final rawType = (m['type'] ?? m['module'])?.toString().trim().toLowerCase() ?? '';
    if (rawType != 'documentslistmodule') continue;
    final c = m['content'];
    if (c is! Map) continue;
    final content = Map<String, dynamic>.from(c);
    final subtitle = (content['subtitle'] ?? '').toString().trim();
    final moduleTitle = (content['moduleTitle'] ?? content['title'] ?? '').toString().trim();
    final description = (content['description'] ?? '').toString().trim();
    final itemsRaw = content['documentItems'];
    final out = <VaultDocumentListItemData>[];
    if (itemsRaw is List) {
      for (final it in itemsRaw) {
        if (it is! Map) continue;
        final row = Map<String, dynamic>.from(it);
        final downloadUrl = (row['downloadUrl'] ?? '').toString().trim();
        if (downloadUrl.isEmpty) continue;
        final displayName = (row['displayName'] ?? row['documentName'] ?? '').toString().trim();
        final dateLabel = (row['dateLabel'] ?? '').toString().trim();
        final mediaId = (row['mediaId'] ?? '').toString().trim();
        out.add(
          VaultDocumentListItemData(
            mediaId: mediaId.isEmpty ? downloadUrl.hashCode.toString() : mediaId,
            downloadUrl: downloadUrl,
            displayName: displayName.isEmpty ? 'Document' : displayName,
            dateLabel: dateLabel,
          ),
        );
      }
    }
    if (out.isEmpty) return null;
    return VaultDocumentsListModuleData(
      subtitle: subtitle,
      moduleTitle: moduleTitle,
      description: description,
      items: out,
    );
  }
  return null;
}

VaultVirtualVisualizationModuleData? virtualVisualizationModuleFromVault(Map<String, dynamic>? vaultData) {
  if (vaultData == null) return null;
  final modules = vaultData['modules'];
  if (modules is! List) return null;
  for (final raw in modules) {
    if (raw is! Map) continue;
    final m = Map<String, dynamic>.from(raw);
    if (m['enabled'] == false) continue;
    final rawType = (m['type'] ?? m['module'])?.toString().trim().toLowerCase() ?? '';
    if (rawType != 'virtualvisualizationmodule') continue;
    final c = m['content'];
    if (c is! Map) continue;
    final content = Map<String, dynamic>.from(c);
    final moduleTitle = (content['moduleTitle'] ?? content['title'] ?? '').toString().trim();
    final description = (content['description'] ?? '').toString().trim();
    final rawUrl = (content['visualizationUrl'] ?? '').toString().trim();
    final normalized = normalizeVirtualVisualizationInput(rawUrl);
    final data = VaultVirtualVisualizationModuleData(
      moduleTitle: moduleTitle,
      description: description,
      normalizedUrl: normalized,
      rawUrl: rawUrl,
    );
    return data.hasRenderableContent ? data : null;
  }
  return null;
}
