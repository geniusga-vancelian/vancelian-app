class Favorite {
  const Favorite({
    required this.id,
    required this.entityType,
    required this.entityId,
    required this.createdAt,
  });

  final String id;
  final String entityType;
  final String entityId;
  final DateTime createdAt;

  factory Favorite.fromJson(Map<String, dynamic> json) {
    return Favorite(
      id: json['id'] as String,
      entityType: json['entity_type'] as String,
      entityId: json['entity_id'] as String,
      createdAt: DateTime.parse(json['created_at'] as String),
    );
  }
}
