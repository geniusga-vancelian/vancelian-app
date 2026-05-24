import '../../../../core/article_editorial_type.dart';

/// Bloc de contenu d'un article
class ArticleBlock {
  final String id;
  final String type;
  final int order;
  final Map<String, dynamic> data;
  final String? imageUrl;

  const ArticleBlock({
    required this.id,
    required this.type,
    required this.order,
    required this.data,
    this.imageUrl,
  });

  factory ArticleBlock.fromJson(Map<String, dynamic> json) {
    final data = json['data'] as Map<String, dynamic>? ?? {};
    return ArticleBlock(
      id: json['id'] as String,
      type: json['type'] as String,
      order: (json['order'] as num?)?.toInt() ?? 0,
      data: Map<String, dynamic>.from(data),
      imageUrl: json['imageUrl'] as String?,
    );
  }
}

/// Catégorie d'article
class ArticleCategory {
  final String id;
  final String slug;
  final String label;

  const ArticleCategory({
    required this.id,
    required this.slug,
    required this.label,
  });

  factory ArticleCategory.fromJson(Map<String, dynamic> json) {
    return ArticleCategory(
      id: json['id'] as String,
      slug: json['slug'] as String,
      label: json['label'] as String,
    );
  }
}

/// Document attaché
class ArticleDocument {
  final String mediaId;
  final String title;
  final String? url;

  const ArticleDocument({
    required this.mediaId,
    required this.title,
    this.url,
  });

  factory ArticleDocument.fromJson(Map<String, dynamic> json) {
    return ArticleDocument(
      mediaId: json['mediaId'] as String,
      title: json['title'] as String? ?? 'Document',
      url: json['url'] as String?,
    );
  }
}

/// Article complet (détail)
class ArticleDetail {
  final String id;
  final String slug;
  final String title;
  final String standfirst;
  final String coverUrl;
  final String? coverTitle;
  final String? coverCredit;
  final String? coverSource;
  final String authorName;
  final String? authorRole;
  final DateTime? publishedAt;
  final DateTime updatedAt;
  final int readingTime;
  final List<String> categorySlugs;
  final List<ArticleCategory> categories;
  final String? videoUrl;
  final List<String> galleryUrls;
  final List<ArticleDocument> documents;
  final List<ArticleBlock> blocks;
  final String articleType;
  final bool isCompanyNews;

  const ArticleDetail({
    required this.id,
    required this.slug,
    required this.title,
    required this.standfirst,
    required this.coverUrl,
    this.coverTitle,
    this.coverCredit,
    this.coverSource,
    required this.authorName,
    this.authorRole,
    this.publishedAt,
    required this.updatedAt,
    required this.readingTime,
    required this.categorySlugs,
    required this.categories,
    this.videoUrl,
    required this.galleryUrls,
    required this.documents,
    required this.blocks,
    this.articleType = 'NEWS',
    this.isCompanyNews = false,
  });

  factory ArticleDetail.fromJson(Map<String, dynamic> json) {
    DateTime? publishedAt;
    if (json['publishedAt'] != null) {
      publishedAt = DateTime.tryParse(json['publishedAt'] as String);
    }
    DateTime updatedAt = DateTime.now();
    if (json['updatedAt'] != null) {
      updatedAt = DateTime.tryParse(json['updatedAt'] as String) ?? updatedAt;
    }
    return ArticleDetail(
      id: json['id'] as String,
      slug: json['slug'] as String,
      title: json['title'] as String,
      standfirst: json['standfirst'] as String,
      coverUrl: json['coverUrl'] as String? ?? '',
      coverTitle: json['coverTitle'] as String?,
      coverCredit: json['coverCredit'] as String?,
      coverSource: json['coverSource'] as String?,
      authorName: json['authorName'] as String,
      authorRole: json['authorRole'] as String?,
      publishedAt: publishedAt,
      updatedAt: updatedAt,
      readingTime: (json['readingTime'] as num?)?.toInt() ?? 0,
      categorySlugs: (json['categorySlugs'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [],
      categories: (json['categories'] as List<dynamic>?)
              ?.map((e) => ArticleCategory.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      videoUrl: json['videoUrl'] as String?,
      galleryUrls: (json['galleryUrls'] as List<dynamic>?)
              ?.map((e) => e.toString())
              .toList() ??
          [],
      documents: (json['documents'] as List<dynamic>?)
              ?.map((e) => ArticleDocument.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      blocks: (json['blocks'] as List<dynamic>?)
              ?.map((e) => ArticleBlock.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      articleType: articleEditorialTypeFromJson(json['articleType']),
      isCompanyNews: json['isCompanyNews'] == true,
    );
  }
}
