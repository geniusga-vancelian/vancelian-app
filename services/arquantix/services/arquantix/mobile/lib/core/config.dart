/// Configuration de l'application
class Config {
  /// URL de base de l'API (Next.js)
  /// En dev: http://localhost:3000 ou http://10.0.2.2:3000 (émulateur Android)
  /// En prod: https://votre-domaine.com
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:3000',
  );

  static String get blogFeedUrl => '$apiBaseUrl/api/blog';
  static String blogArticleUrl(String slug) => '$apiBaseUrl/api/blog/$slug';
}
