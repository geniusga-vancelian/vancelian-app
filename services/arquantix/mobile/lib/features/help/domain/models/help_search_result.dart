class HelpSearchResult {
  const HelpSearchResult({
    required this.id,
    required this.slug,
    required this.question,
    required this.snippet,
    required this.collectionSlug,
    required this.collectionTitle,
    required this.categorySlug,
    required this.categoryTitle,
    this.updatedAt,
  });

  final String id;
  final String slug;
  final String question;
  final String snippet;
  final String collectionSlug;
  final String collectionTitle;
  final String categorySlug;
  final String categoryTitle;
  final DateTime? updatedAt;

  factory HelpSearchResult.fromJson(Map<String, dynamic> json) {
    final collection = (json['collection'] as Map<String, dynamic>?) ?? const {};
    final category = (json['category'] as Map<String, dynamic>?) ?? const {};
    return HelpSearchResult(
      id: (json['id'] ?? '').toString(),
      slug: (json['slug'] ?? '').toString(),
      question: (json['question'] ?? '').toString(),
      snippet: (json['snippet'] ?? '').toString(),
      collectionSlug: (collection['slug'] ?? '').toString(),
      collectionTitle: (collection['title'] ?? '').toString(),
      categorySlug: (category['slug'] ?? '').toString(),
      categoryTitle: (category['title'] ?? '').toString(),
      updatedAt: DateTime.tryParse((json['updatedAt'] ?? '').toString()),
    );
  }
}
