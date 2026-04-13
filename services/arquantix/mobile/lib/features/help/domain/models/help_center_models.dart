class HelpTargetTag {
  const HelpTargetTag({
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

  factory HelpTargetTag.fromJson(Map<String, dynamic> json) {
    return HelpTargetTag(
      type: (json['type'] ?? '').toString(),
      id: (json['id'] ?? '').toString(),
      slug: (json['slug'] ?? '').toString(),
      label: (json['label'] ?? '').toString(),
    );
  }
}

class HelpCollectionItem {
  const HelpCollectionItem({
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

  factory HelpCollectionItem.fromJson(Map<String, dynamic> json) {
    return HelpCollectionItem(
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

class HelpCategoryItem {
  const HelpCategoryItem({
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

  factory HelpCategoryItem.fromJson(Map<String, dynamic> json) {
    return HelpCategoryItem(
      id: (json['id'] ?? '').toString(),
      slug: (json['slug'] ?? '').toString(),
      title: (json['title'] ?? '').toString(),
      description: json['description']?.toString(),
      articleCount: (json['articleCount'] as num?)?.toInt() ?? 0,
    );
  }
}

class HelpCategoryListResponse {
  const HelpCategoryListResponse({
    required this.collectionSlug,
    required this.collectionTitle,
    required this.categories,
  });

  final String collectionSlug;
  final String collectionTitle;
  final List<HelpCategoryItem> categories;

  factory HelpCategoryListResponse.fromJson(Map<String, dynamic> json) {
    final collection = (json['collection'] as Map<String, dynamic>? ?? const {});
    final categoriesRaw = (json['categories'] as List<dynamic>? ?? const []);
    return HelpCategoryListResponse(
      collectionSlug: (collection['slug'] ?? '').toString(),
      collectionTitle: (collection['title'] ?? '').toString(),
      categories: categoriesRaw
          .whereType<Map<String, dynamic>>()
          .map(HelpCategoryItem.fromJson)
          .where((item) => item.slug.isNotEmpty && item.title.isNotEmpty)
          .toList(),
    );
  }
}

class HelpArticleItem {
  const HelpArticleItem({
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
  final List<HelpTargetTag> targetTags;
  final String? standfirst;
  final DateTime? updatedAt;
  final DateTime? publishedAt;

  factory HelpArticleItem.fromJson(Map<String, dynamic> json) {
    return HelpArticleItem(
      id: (json['id'] ?? '').toString(),
      slug: (json['slug'] ?? '').toString(),
      question: (json['question'] ?? '').toString(),
      targetTags: (json['targetTags'] as List<dynamic>? ?? const [])
          .whereType<Map<String, dynamic>>()
          .map(HelpTargetTag.fromJson)
          .where((tag) => tag.type.isNotEmpty && tag.id.isNotEmpty && tag.label.isNotEmpty)
          .toList(),
      standfirst: json['standfirst']?.toString(),
      updatedAt: DateTime.tryParse((json['updatedAt'] ?? '').toString()),
      publishedAt: DateTime.tryParse((json['publishedAt'] ?? '').toString()),
    );
  }
}

class HelpArticleListResponse {
  const HelpArticleListResponse({
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
  final List<HelpArticleItem> articles;

  factory HelpArticleListResponse.fromJson(Map<String, dynamic> json) {
    final collection = (json['collection'] as Map<String, dynamic>? ?? const {});
    final category = (json['category'] as Map<String, dynamic>? ?? const {});
    final listRaw = (json['articles'] as List<dynamic>? ?? const []);
    return HelpArticleListResponse(
      collectionSlug: (collection['slug'] ?? '').toString(),
      collectionTitle: (collection['title'] ?? '').toString(),
      categorySlug: (category['slug'] ?? '').toString(),
      categoryTitle: (category['title'] ?? '').toString(),
      articles: listRaw
          .whereType<Map<String, dynamic>>()
          .map(HelpArticleItem.fromJson)
          .where((item) => item.slug.isNotEmpty && item.question.isNotEmpty)
          .toList(),
    );
  }
}

class HelpTaggedArticleItem {
  const HelpTaggedArticleItem({
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

  factory HelpTaggedArticleItem.fromJson(Map<String, dynamic> json) {
    final collection = (json['collection'] as Map<String, dynamic>? ?? const {});
    final category = (json['category'] as Map<String, dynamic>? ?? const {});
    return HelpTaggedArticleItem(
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

class HelpArticleBlock {
  const HelpArticleBlock({
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

  factory HelpArticleBlock.fromJson(Map<String, dynamic> json) {
    return HelpArticleBlock(
      id: (json['id'] ?? '').toString(),
      type: (json['type'] ?? '').toString(),
      order: (json['order'] as num?)?.toInt() ?? 0,
      data: Map<String, dynamic>.from((json['data'] as Map<String, dynamic>? ?? const {})),
      imageUrl: json['imageUrl']?.toString(),
    );
  }
}

class HelpArticleDetail {
  const HelpArticleDetail({
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
    this.updatedAt,
    this.publishedAt,
  });

  final String id;
  final String slug;
  final String question;
  final String standfirst;
  final String markdownContent;
  final String collectionSlug;
  final String collectionTitle;
  final String categorySlug;
  final String categoryTitle;
  final List<HelpArticleBlock> blocks;
  final DateTime? updatedAt;
  final DateTime? publishedAt;

  factory HelpArticleDetail.fromJson(Map<String, dynamic> json) {
    final collection = (json['collection'] as Map<String, dynamic>? ?? const {});
    final category = (json['category'] as Map<String, dynamic>? ?? const {});
    final blocksRaw = (json['blocks'] as List<dynamic>? ?? const []);
    return HelpArticleDetail(
      id: (json['id'] ?? '').toString(),
      slug: (json['slug'] ?? '').toString(),
      question: (json['question'] ?? '').toString(),
      standfirst: (json['standfirst'] ?? '').toString(),
      markdownContent: (json['markdownContent'] ?? '').toString(),
      collectionSlug: (collection['slug'] ?? '').toString(),
      collectionTitle: (collection['title'] ?? '').toString(),
      categorySlug: (category['slug'] ?? '').toString(),
      categoryTitle: (category['title'] ?? '').toString(),
      blocks: blocksRaw
          .whereType<Map<String, dynamic>>()
          .map(HelpArticleBlock.fromJson)
          .toList(),
      updatedAt: DateTime.tryParse((json['updatedAt'] ?? '').toString()),
      publishedAt: DateTime.tryParse((json['publishedAt'] ?? '').toString()),
    );
  }
}
