/// Modèles DTO pour le module Academy mobile.
///
/// Symétriques aux modèles Help (`help_center_models.dart`) — on garde la
/// même shape JSON côté API pour faciliter les pickers / partage de widgets
/// si jamais on en avait besoin.
class AcademyTargetTag {
  const AcademyTargetTag({
    required this.type,
    required this.id,
    required this.slug,
    required this.label,
  });

  final String type;
  final String id;
  final String slug;
  final String label;

  String get key => '$type:$id';

  factory AcademyTargetTag.fromJson(Map<String, dynamic> json) {
    return AcademyTargetTag(
      type: (json['type'] ?? '').toString(),
      id: (json['id'] ?? '').toString(),
      slug: (json['slug'] ?? '').toString(),
      label: (json['label'] ?? '').toString(),
    );
  }
}

class AcademyCollectionItem {
  const AcademyCollectionItem({
    required this.id,
    required this.slug,
    required this.title,
    this.subtitle,
    this.description,
    this.iconKey,
    this.colorHex,
    this.articleCount = 0,
  });

  final String id;
  final String slug;
  final String title;
  final String? subtitle;
  final String? description;
  final String? iconKey;
  final String? colorHex;
  final int articleCount;

  factory AcademyCollectionItem.fromJson(Map<String, dynamic> json) {
    return AcademyCollectionItem(
      id: (json['id'] ?? '').toString(),
      slug: (json['slug'] ?? '').toString(),
      title: (json['title'] ?? '').toString(),
      subtitle: json['subtitle']?.toString(),
      description: json['description']?.toString(),
      iconKey: json['iconKey']?.toString(),
      colorHex: json['colorHex']?.toString(),
      articleCount: (json['articleCount'] as num?)?.toInt() ?? 0,
    );
  }
}

class AcademyCategoryItem {
  const AcademyCategoryItem({
    required this.id,
    required this.slug,
    required this.title,
    this.description,
    this.articleCount = 0,
  });

  final String id;
  final String slug;
  final String title;
  final String? description;
  final int articleCount;

  factory AcademyCategoryItem.fromJson(Map<String, dynamic> json) {
    return AcademyCategoryItem(
      id: (json['id'] ?? '').toString(),
      slug: (json['slug'] ?? '').toString(),
      title: (json['title'] ?? '').toString(),
      description: json['description']?.toString(),
      articleCount: (json['articleCount'] as num?)?.toInt() ?? 0,
    );
  }
}

class AcademyCategoryListResponse {
  const AcademyCategoryListResponse({
    required this.collectionSlug,
    required this.collectionTitle,
    required this.categories,
  });

  final String collectionSlug;
  final String collectionTitle;
  final List<AcademyCategoryItem> categories;

  factory AcademyCategoryListResponse.fromJson(Map<String, dynamic> json) {
    final collection = (json['collection'] as Map<String, dynamic>? ?? const {});
    final categoriesRaw = (json['categories'] as List<dynamic>? ?? const []);
    return AcademyCategoryListResponse(
      collectionSlug: (collection['slug'] ?? '').toString(),
      collectionTitle: (collection['title'] ?? '').toString(),
      categories: categoriesRaw
          .whereType<Map<String, dynamic>>()
          .map(AcademyCategoryItem.fromJson)
          .where((item) => item.slug.isNotEmpty && item.title.isNotEmpty)
          .toList(),
    );
  }
}

class AcademyArticleItem {
  const AcademyArticleItem({
    required this.id,
    required this.slug,
    required this.question,
    this.targetTags = const [],
    this.standfirst,
    this.updatedAt,
    this.publishedAt,
  });

  final String id;
  final String slug;
  final String question;
  final List<AcademyTargetTag> targetTags;
  final String? standfirst;
  final DateTime? updatedAt;
  final DateTime? publishedAt;

  factory AcademyArticleItem.fromJson(Map<String, dynamic> json) {
    return AcademyArticleItem(
      id: (json['id'] ?? '').toString(),
      slug: (json['slug'] ?? '').toString(),
      question: (json['question'] ?? '').toString(),
      targetTags: (json['targetTags'] as List<dynamic>? ?? const [])
          .whereType<Map<String, dynamic>>()
          .map(AcademyTargetTag.fromJson)
          .where((tag) => tag.type.isNotEmpty && tag.id.isNotEmpty && tag.label.isNotEmpty)
          .toList(),
      standfirst: json['standfirst']?.toString(),
      updatedAt: DateTime.tryParse((json['updatedAt'] ?? '').toString()),
      publishedAt: DateTime.tryParse((json['publishedAt'] ?? '').toString()),
    );
  }
}

class AcademyArticleListResponse {
  const AcademyArticleListResponse({
    required this.collectionSlug,
    required this.collectionTitle,
    required this.categorySlug,
    required this.categoryTitle,
    required this.articles,
  });

  final String collectionSlug;
  final String collectionTitle;
  final String categorySlug;
  final String categoryTitle;
  final List<AcademyArticleItem> articles;

  factory AcademyArticleListResponse.fromJson(Map<String, dynamic> json) {
    final collection = (json['collection'] as Map<String, dynamic>? ?? const {});
    final category = (json['category'] as Map<String, dynamic>? ?? const {});
    final listRaw = (json['articles'] as List<dynamic>? ?? const []);
    return AcademyArticleListResponse(
      collectionSlug: (collection['slug'] ?? '').toString(),
      collectionTitle: (collection['title'] ?? '').toString(),
      categorySlug: (category['slug'] ?? '').toString(),
      categoryTitle: (category['title'] ?? '').toString(),
      articles: listRaw
          .whereType<Map<String, dynamic>>()
          .map(AcademyArticleItem.fromJson)
          .where((item) => item.slug.isNotEmpty && item.question.isNotEmpty)
          .toList(),
    );
  }
}

class AcademyTaggedArticleItem {
  const AcademyTaggedArticleItem({
    required this.id,
    required this.slug,
    required this.question,
    required this.collectionSlug,
    required this.collectionTitle,
    required this.categorySlug,
    required this.categoryTitle,
    this.standfirst,
    this.updatedAt,
  });

  final String id;
  final String slug;
  final String question;
  final String collectionSlug;
  final String collectionTitle;
  final String categorySlug;
  final String categoryTitle;
  final String? standfirst;
  final DateTime? updatedAt;

  factory AcademyTaggedArticleItem.fromJson(Map<String, dynamic> json) {
    final collection = (json['collection'] as Map<String, dynamic>? ?? const {});
    final category = (json['category'] as Map<String, dynamic>? ?? const {});
    return AcademyTaggedArticleItem(
      id: (json['id'] ?? '').toString(),
      slug: (json['slug'] ?? '').toString(),
      question: (json['question'] ?? '').toString(),
      standfirst: json['standfirst']?.toString(),
      collectionSlug: (collection['slug'] ?? '').toString(),
      collectionTitle: (collection['title'] ?? '').toString(),
      categorySlug: (category['slug'] ?? '').toString(),
      categoryTitle: (category['title'] ?? '').toString(),
      updatedAt: DateTime.tryParse((json['updatedAt'] ?? '').toString()),
    );
  }
}

class AcademyArticleBlock {
  const AcademyArticleBlock({
    required this.id,
    required this.type,
    required this.order,
    required this.data,
    this.imageUrl,
  });

  final String id;
  final String type;
  final int order;
  final Map<String, dynamic> data;
  final String? imageUrl;

  factory AcademyArticleBlock.fromJson(Map<String, dynamic> json) {
    return AcademyArticleBlock(
      id: (json['id'] ?? '').toString(),
      type: (json['type'] ?? '').toString(),
      order: (json['order'] as num?)?.toInt() ?? 0,
      data: Map<String, dynamic>.from((json['data'] as Map<String, dynamic>? ?? const {})),
      imageUrl: json['imageUrl']?.toString(),
    );
  }
}

class AcademyArticleDetail {
  const AcademyArticleDetail({
    required this.id,
    required this.slug,
    required this.question,
    required this.standfirst,
    required this.markdownContent,
    required this.collectionSlug,
    required this.collectionTitle,
    required this.categorySlug,
    required this.categoryTitle,
    required this.blocks,
    this.coverUrl = '',
    this.collectionIconKey,
    this.collectionColorHex,
    this.updatedAt,
    this.publishedAt,
  });

  final String id;
  final String slug;
  final String question;
  final String standfirst;
  final String coverUrl;
  final String markdownContent;
  final String collectionSlug;
  final String collectionTitle;
  final String? collectionIconKey;
  final String? collectionColorHex;
  final String categorySlug;
  final String categoryTitle;
  final List<AcademyArticleBlock> blocks;
  final DateTime? updatedAt;
  final DateTime? publishedAt;

  factory AcademyArticleDetail.fromJson(Map<String, dynamic> json) {
    final collection = (json['collection'] as Map<String, dynamic>? ?? const {});
    final category = (json['category'] as Map<String, dynamic>? ?? const {});
    final blocksRaw = (json['blocks'] as List<dynamic>? ?? const []);
    return AcademyArticleDetail(
      id: (json['id'] ?? '').toString(),
      slug: (json['slug'] ?? '').toString(),
      question: (json['question'] ?? '').toString(),
      standfirst: (json['standfirst'] ?? '').toString(),
      coverUrl: (json['coverUrl'] ?? '').toString(),
      markdownContent: (json['markdownContent'] ?? '').toString(),
      collectionSlug: (collection['slug'] ?? '').toString(),
      collectionTitle: (collection['title'] ?? '').toString(),
      collectionIconKey: collection['iconKey']?.toString(),
      collectionColorHex: collection['colorHex']?.toString(),
      categorySlug: (category['slug'] ?? '').toString(),
      categoryTitle: (category['title'] ?? '').toString(),
      blocks: blocksRaw
          .whereType<Map<String, dynamic>>()
          .map(AcademyArticleBlock.fromJson)
          .toList(),
      updatedAt: DateTime.tryParse((json['updatedAt'] ?? '').toString()),
      publishedAt: DateTime.tryParse((json['publishedAt'] ?? '').toString()),
    );
  }
}
