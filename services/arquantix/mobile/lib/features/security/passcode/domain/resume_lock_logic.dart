/// Logique pure pour le relock au resume (facile à tester sans binding Flutter).
bool shouldRequireResumeUnlock({
  required DateTime? pausedAt,
  required DateTime now,
  required Duration threshold,
}) {
  if (pausedAt == null) return false;
  return now.difference(pausedAt) >= threshold;
}
