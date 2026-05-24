/// Valeurs `articleType` côté API (articles blog / research).
String articleEditorialTypeFromJson(dynamic value) {
  final s = value?.toString().toUpperCase() ?? 'NEWS';
  if (s == 'ANALYSIS') return 'ANALYSIS';
  if (s == 'RESEARCH') return 'RESEARCH';
  return 'NEWS';
}

/// Libellé court pour badges liste / hero (vide → traiter comme marché / company côté UI).
String editorialBadgeLabel(String articleType) {
  final u = articleType.toUpperCase();
  if (u == 'ANALYSIS') return 'Analysis';
  if (u == 'RESEARCH') return 'Research';
  return '';
}
