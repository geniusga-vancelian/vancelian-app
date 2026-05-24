import '../../../../core/article_editorial_type.dart';

/// Article preview (liste / feed)
class ArticlePreview {
  final String id;
  final String slug;
  final String title;
  final String standfirst;
  final String coverUrl;
  final String authorName;
  final String? authorRole;
  final DateTime? publishedAt;
  final int readingTime;
  final List<String>? categorySlugs;
  final bool isMilestone;
  final String articleType;
  /// Actualité entreprise (NEWS uniquement ; dérivé API + legacy slug vancelian).
  final bool isCompanyNews;
  /// IDs des projets auxquels l'article est lié (pour filtrer "news du projet"). Non lié à la catégorie.
  final List<String>? projectIds;

  const ArticlePreview({
    required this.id,
    required this.slug,
    required this.title,
    required this.standfirst,
    required this.coverUrl,
    required this.authorName,
    this.authorRole,
    this.publishedAt,
    required this.readingTime,
    this.categorySlugs,
    this.isMilestone = false,
    this.articleType = 'NEWS',
    this.isCompanyNews = false,
    this.projectIds,
  });

  /// True si cet article est lié au projet [projectId].
  bool isLinkedToProject(String projectId) =>
      projectIds != null && projectIds!.isNotEmpty && projectIds!.contains(projectId);

  factory ArticlePreview.fromJson(Map<String, dynamic> json) {
    DateTime? publishedAt;
    if (json['publishedAt'] != null) {
      publishedAt = DateTime.tryParse(json['publishedAt'] as String);
    }
    final projectIdsRaw = json['projectIds'] ?? json['projectId'];
    List<String>? projectIds;
    if (projectIdsRaw is List) {
      projectIds = projectIdsRaw.map((e) => e?.toString() ?? '').where((s) => s.isNotEmpty).toList();
    } else if (projectIdsRaw is String && projectIdsRaw.isNotEmpty) {
      projectIds = [projectIdsRaw];
    }
    return ArticlePreview(
      id: json['id'] as String,
      slug: json['slug'] as String,
      title: json['title'] as String,
      standfirst: json['standfirst'] as String,
      coverUrl: json['coverUrl'] as String? ?? '',
      authorName: json['authorName'] as String,
      authorRole: json['authorRole'] as String?,
      publishedAt: publishedAt,
      readingTime: (json['readingTime'] as num?)?.toInt() ?? 0,
      categorySlugs: (json['categorySlugs'] as List<dynamic>?)
          ?.map((e) => e.toString())
          .toList(),
      isMilestone: json['isMilestone'] == true,
      articleType: articleEditorialTypeFromJson(json['articleType']),
      isCompanyNews: json['isCompanyNews'] == true,
      projectIds: projectIds,
    );
  }
}
