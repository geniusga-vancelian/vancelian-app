import 'dart:convert';

/// Réponse élément de GET /api/mobile/flutter/catalog/products
class CatalogListItem {
  CatalogListItem({
    required this.id,
    required this.slug,
    this.legacyProjectId,
    required this.productType,
    required this.title,
    this.subtitle,
    this.coverUrl,
    this.categorySlug,
    required this.engine,
  });

  final String id;
  final String slug;
  final String? legacyProjectId;
  final String productType;
  final String title;
  final String? subtitle;
  final String? coverUrl;
  final String? categorySlug;
  final CatalogEngineBlock engine;

  factory CatalogListItem.fromJson(Map<String, dynamic> json) {
    return CatalogListItem(
      id: json['id'] as String? ?? '',
      slug: json['slug'] as String? ?? '',
      legacyProjectId: json['legacyProjectId'] as String?,
      productType: json['productType'] as String? ?? '',
      title: json['title'] as String? ?? '',
      subtitle: json['subtitle'] as String?,
      coverUrl: json['coverUrl'] as String?,
      categorySlug: json['category'] as String?,
      engine: CatalogEngineBlock.fromJson(json['engine'] as Map<String, dynamic>? ?? const {}),
    );
  }
}

class CatalogEngineBlock {
  CatalogEngineBlock({
    this.type,
    this.referenceId,
    this.snapshot,
  });

  final String? type;
  final String? referenceId;
  final Map<String, dynamic>? snapshot;

  factory CatalogEngineBlock.fromJson(Map<String, dynamic> json) {
    final snap = json['snapshot'];
    return CatalogEngineBlock(
      type: json['type'] as String?,
      referenceId: json['referenceId'] as String?,
      snapshot: snap is Map<String, dynamic> ? snap : null,
    );
  }
}

/// Réponse GET /api/mobile/flutter/catalog/products/{slug}
class CatalogProductDetail {
  CatalogProductDetail({
    required this.packagedProduct,
    required this.presentation,
    this.vaultData,
    required this.engine,
  });

  final CatalogPackagedMeta packagedProduct;
  final CatalogPresentation presentation;
  final Map<String, dynamic>? vaultData;
  final CatalogEngineBlock engine;

  factory CatalogProductDetail.fromJson(Map<String, dynamic> json) {
    final vault = json['vault'] as Map<String, dynamic>?;
    final data = vault != null ? vault['data'] : null;
    return CatalogProductDetail(
      packagedProduct: CatalogPackagedMeta.fromJson(
        json['packagedProduct'] as Map<String, dynamic>? ?? const {},
      ),
      presentation: CatalogPresentation.fromJson(
        json['presentation'] as Map<String, dynamic>? ?? const {},
      ),
      vaultData: data is Map<String, dynamic> ? data : null,
      engine: CatalogEngineBlock.fromJson(json['engine'] as Map<String, dynamic>? ?? const {}),
    );
  }

  static CatalogProductDetail parse(String body) =>
      CatalogProductDetail.fromJson(jsonDecode(body) as Map<String, dynamic>);
}

class CatalogPackagedMeta {
  CatalogPackagedMeta({
    required this.id,
    required this.slug,
    this.legacyProjectId,
    required this.productType,
    this.categorySlug,
    this.tags,
  });

  final String id;
  final String slug;
  final String? legacyProjectId;
  final String productType;
  final String? categorySlug;
  final List<String>? tags;

  factory CatalogPackagedMeta.fromJson(Map<String, dynamic> json) {
    final tagsRaw = json['tags'];
    return CatalogPackagedMeta(
      id: json['id'] as String? ?? '',
      slug: json['slug'] as String? ?? '',
      legacyProjectId: json['legacyProjectId'] as String?,
      productType: json['productType'] as String? ?? '',
      categorySlug: json['categorySlug'] as String?,
      tags: tagsRaw is List
          ? tagsRaw.map((e) => e.toString()).where((s) => s.isNotEmpty).toList()
          : null,
    );
  }
}

class CatalogPresentation {
  CatalogPresentation({
    required this.title,
    this.subtitle,
    this.coverUrl,
  });

  final String title;
  final String? subtitle;
  final String? coverUrl;

  factory CatalogPresentation.fromJson(Map<String, dynamic> json) {
    return CatalogPresentation(
      title: json['title'] as String? ?? '',
      subtitle: json['subtitle'] as String?,
      coverUrl: json['coverUrl'] as String?,
    );
  }
}
