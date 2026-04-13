import 'package:package_info_plus/package_info_plus.dart';

/// Source de vérité version / build alignée sur `pubspec.yaml` (via génération plateforme).
class AppInfoService {
  static String? _version;
  static String? _buildNumber;

  static Future<void> init() async {
    try {
      final info = await PackageInfo.fromPlatform();
      _version = info.version;
      _buildNumber = info.buildNumber;
    } catch (_) {
      // Ne jamais faire échouer le démarrage si le plugin échoue (tests, plateforme atypique).
      _version = null;
      _buildNumber = null;
    }
  }

  static String get version => _version ?? 'unknown';

  static String get build => _buildNumber ?? '0';

  static String get fullVersion => '$version+$build';
}
