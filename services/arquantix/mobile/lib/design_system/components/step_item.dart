/// Modèle de données pour une étape du module Steps (Itinerary / Étapes).
class StepItem {
  const StepItem({
    required this.title,
    this.index,
    this.dayLabel,
    this.date,
    this.description,
    this.tags = const [],
    this.imageUrl,
    this.isCompleted = false,
  });

  /// Numéro d’étape (1..N). Si null, dérivé de la position dans la liste.
  final int? index;

  /// Ex. "Day 1" (optionnel).
  final String? dayLabel;

  /// Date affichée en premier en haut de la carte (ex. "15 mars 2025").
  final String? date;

  final String title;

  /// Ex. "Explore Shibuya Crossing..."
  final String? description;

  /// Ex. ["Shopping", "Culture"]
  final List<String> tags;

  /// URL ou chemin de la miniature.
  final String? imageUrl;

  /// Pour futur état done/pending.
  final bool isCompleted;

  /// Crée une copie avec [index] défini (utile quand l’index est calculé côté liste).
  StepItem withIndex(int index) => StepItem(
        index: index,
        dayLabel: dayLabel,
        date: date,
        title: title,
        description: description,
        tags: tags,
        imageUrl: imageUrl,
        isCompleted: isCompleted,
      );

  /// Désérialisation JSON pour chargement dynamique de modules.
  /// Structure attendue : { "dayLabel"?,"date"?,"title","description"?,"tags"?,"imageUrl"?,"isCompleted"? }
  static StepItem? fromJson(dynamic json) {
    if (json is! Map<String, dynamic>) return null;
    final title = json['title'] as String?;
    if (title == null || title.isEmpty) return null;
    final tagsRaw = json['tags'];
    final tags = tagsRaw is List
        ? tagsRaw.map((e) => e?.toString() ?? '').where((s) => s.isNotEmpty).toList()
        : <String>[];
    return StepItem(
      index: json['index'] as int?,
      dayLabel: json['dayLabel'] as String?,
      date: json['date'] as String?,
      title: title,
      description: json['description'] as String?,
      tags: tags,
      imageUrl: json['imageUrl'] as String?,
      isCompleted: json['isCompleted'] == true,
    );
  }

  /// Liste d’étapes depuis un tableau JSON.
  static List<StepItem> listFromJson(dynamic json) {
    if (json is! List) return [];
    final list = <StepItem>[];
    for (var i = 0; i < json.length; i++) {
      final item = StepItem.fromJson(json[i]);
      if (item != null) list.add(item.withIndex(i + 1));
    }
    return list;
  }
}
