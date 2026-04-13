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
  });

  factory ArticlePreview.fromJson(Map<String, dynamic> json) {
    DateTime? publishedAt;
    if (json['publishedAt'] != null) {
      publishedAt = DateTime.tryParse(json['publishedAt'] as String);
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
    );
  }
}
