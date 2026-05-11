import 'dart:math' as math;

import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../atoms/atoms.dart';
import 'kalai_icon.dart';

/// Normalise une saisie marketing : iframe Google Maps complète → URL du `src` ;
/// décodage des entités HTML ([&#39;] → `'`, [&amp;] → `&`, etc.).
String normalizeLocalisationEmbedInput(String raw) {
  var s = raw.trim();
  if (s.isEmpty) return '';
  if (RegExp(r'<iframe\b', caseSensitive: false).hasMatch(s)) {
    final src = _extractIframeSrcFromHtml(s);
    if (src != null && src.isNotEmpty) s = src;
  }
  return _decodeMinimalHtmlEntities(s).trim();
}

String _decodeMinimalHtmlEntities(String input) {
  var out = input
      .replaceAllMapped(RegExp(r'&#(\d+);'), (m) {
        final code = int.tryParse(m[1] ?? '');
        if (code == null || code < 0 || code > 0x10ffff) return m[0] ?? '';
        return String.fromCharCode(code);
      })
      .replaceAllMapped(RegExp(r'&#x([\da-fA-F]+);'), (m) {
        final code = int.tryParse(m[1] ?? '', radix: 16);
        if (code == null || code < 0 || code > 0x10ffff) return m[0] ?? '';
        return String.fromCharCode(code);
      });
  out = out
      .replaceAll('&quot;', '"')
      .replaceAll('&apos;', "'")
      .replaceAll('&#39;', "'")
      .replaceAll('&lt;', '<')
      .replaceAll('&gt;', '>')
      .replaceAll('&amp;', '&');
  return out;
}

String? _extractIframeSrcFromHtml(String html) {
  final quoted = RegExp(
    r'''<iframe\b[^>]*\bsrc\s*=\s*(["'])([\s\S]*?)\1''',
    caseSensitive: false,
  );
  final mq = quoted.firstMatch(html);
  if (mq != null) {
    final v = mq.group(2)?.trim();
    if (v != null && v.isNotEmpty) return v;
  }
  final bare = RegExp(
    r'<iframe\b[^>]*\bsrc\s*=\s*([^\s>]+)',
    caseSensitive: false,
  );
  final mb = bare.firstMatch(html);
  if (mb != null) {
    var v = mb.group(1)?.trim() ?? '';
    v = v.replaceAll('"', '').replaceAll("'", '');
    if (v.isNotEmpty) return v;
  }
  return null;
}

/// Carte « localisation » : zone carte (preview statique) + texte, sans barre de funding ni tags.
///
/// Structure alignée sur [InvestmentCard] (hauteur de zone média 242 px, relief type DS).
/// Le bouton pilule ouvre Google Maps dans le navigateur ([LaunchMode.externalApplication]).
///
/// La preview utilise **OpenStreetMap Static Map** (pas de clé API requise).
/// L'ancienne approche WebView échouait silencieusement sur Flutter Web
/// (`webview_flutter_web` ne supporte ni `enableZoom`, ni `setUserAgent`…)
/// et affichait souvent une page blanche / consent RGPD sur iOS/macOS.
class LocalisationCard extends StatelessWidget {
  const LocalisationCard({
    super.key,
    required this.embedUrl,
    required this.complement,
    this.addressTitle = 'Adresse',
    this.externalMapUrl,
    this.mapsButtonLabel = 'Agrandir la carte',
  });

  /// URL d'embed Google Maps (mêmes règles que [isAllowedEmbedUrl]).
  final String embedUrl;

  /// Ligne secondaire (ex. complément d'adresse) sous [addressTitle].
  final String complement;

  /// Titre de la zone texte (sous la carte), ex. « Adresse ».
  final String addressTitle;

  /// URL ouverte par le bouton si renseignée ; sinon repli sur [embedUrl] puis recherche Maps.
  final String? externalMapUrl;

  final String mapsButtonLabel;

  /// Hauteur de la zone carte (identique à la zone image de [InvestmentCard]).
  static const double mapHeight = 242;

  // ──────────────────────────────────────────────────────────────────────────
  // Validation embed URL (rétrocompatible avec les call-sites existants)
  // ──────────────────────────────────────────────────────────────────────────

  /// Autorise uniquement les embeds Google Maps (sécurité).
  static bool isAllowedEmbedUrl(String raw) {
    final t = normalizeLocalisationEmbedInput(raw);
    if (t.isEmpty) return false;
    final uri = Uri.tryParse(t.startsWith('http') ? t : 'https://$t');
    if (uri == null) return false;
    final host = uri.host.toLowerCase();
    final googleHost = host == 'google.com' ||
        host == 'www.google.com' ||
        host == 'maps.google.com' ||
        host.endsWith('.google.com');
    if (!googleHost) return false;
    if (uri.path.contains('/maps/embed')) return true;
    if (uri.queryParameters['output'] == 'embed') {
      final p = uri.path;
      if (p == '/maps' || p.startsWith('/maps/')) return true;
    }
    return false;
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Extraction de coordonnées depuis l'URL embed
  // ──────────────────────────────────────────────────────────────────────────

  static final _qRegex =
      RegExp(r'[?&]q=(-?\d+\.?\d*)[,%2C]+(-?\d+\.?\d*)', caseSensitive: false);
  static final _pbRegex = RegExp(r'!3d(-?\d+\.?\d*)!4d(-?\d+\.?\d*)');
  static final _atRegex = RegExp(r'@(-?\d+\.?\d*),(-?\d+\.?\d*)');

  /// Extrait (lat, lng) depuis une URL d'embed Google Maps.
  static ({double lat, double lng})? extractCoords(String embedUrl) {
    final t = normalizeLocalisationEmbedInput(embedUrl);
    for (final re in [_qRegex, _pbRegex, _atRegex]) {
      final m = re.firstMatch(t);
      if (m != null) {
        final lat = double.tryParse(m.group(1)!);
        final lng = double.tryParse(m.group(2)!);
        if (lat != null && lng != null && lat.abs() <= 90 && lng.abs() <= 180) {
          return (lat: lat, lng: lng);
        }
      }
    }
    return null;
  }

  // ──────────────────────────────────────────────────────────────────────────
  // URL de la carte statique (OpenStreetMap — pas de clé API)
  // ──────────────────────────────────────────────────────────────────────────

  /// Calcule le numéro de tuile OSM pour un (lat, lng, zoom).
  static int _tileX(double lng, int z) =>
      ((lng + 180) / 360 * (1 << z)).floor();

  static int _tileY(double lat, int z) {
    final latRad = lat * math.pi / 180;
    return ((1 - math.log(math.tan(latRad) + 1 / math.cos(latRad)) / math.pi) /
            2 *
            (1 << z))
        .floor();
  }

  /// URL d'une seule tuile OSM 256×256 px centrée sur (lat, lng).
  static String osmTileUrl(double lat, double lng, {int zoom = 15}) {
    final x = _tileX(lng, zoom);
    final y = _tileY(lat, zoom);
    return 'https://tile.openstreetmap.org/$zoom/$x/$y.png';
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Build
  // ──────────────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final title = addressTitle.trim();
    final comp = complement.trim();
    final embed = normalizeLocalisationEmbedInput(embedUrl);
    final coords = extractCoords(embed);

    return Container(
      clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(
        color: AppColors.white,
        borderRadius: BorderRadius.circular(AppRadius.xxl),
        boxShadow: const [
          BoxShadow(
            blurRadius: 20,
            spreadRadius: -10,
            color: Color(0x1F000000),
          ),
        ],
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SizedBox(
            height: mapHeight,
            child: Stack(
              fit: StackFit.expand,
              children: [
                _buildMapPreview(coords),
                Positioned(
                  top: AppSpacing.s3,
                  left: AppSpacing.s3,
                  child: _buildMapsButton(),
                ),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(
              AppSpacing.s4,
              AppSpacing.s4,
              AppSpacing.s4,
              AppSpacing.s6,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                if (title.isNotEmpty)
                  Text(
                    title,
                    style: AppTypography.itemPrimary.copyWith(
                      color: AppColors.black,
                    ),
                  ),
                if (title.isNotEmpty && comp.isNotEmpty)
                  const SizedBox(height: AppSpacing.s2),
                if (comp.isNotEmpty)
                  Text(
                    comp,
                    style: AppTypography.itemSupporting.copyWith(
                      color: AppColors.gray,
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Sub-widgets
  // ──────────────────────────────────────────────────────────────────────────

  /// Grille de 3×2 tuiles OSM pour couvrir la zone de la carte (768×512 px → couvre 242 px de haut).
  Widget _buildMapPreview(({double lat, double lng})? coords) {
    if (coords == null) {
      return const ColoredBox(
        color: Color(0xFFE8E8E8),
        child: Center(
          child: KalaiIcon(KalaiIcons.map, color: AppColors.gray, size: 40),
        ),
      );
    }

    const zoom = 15;
    final cx = _tileX(coords.lng, zoom);
    final cy = _tileY(coords.lat, zoom);
    const cols = 3;
    const rows = 2;
    const tileSize = 256.0;

    return ClipRect(
      child: OverflowBox(
        maxWidth: cols * tileSize,
        maxHeight: rows * tileSize,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: List.generate(rows, (row) {
            return Row(
              mainAxisSize: MainAxisSize.min,
              children: List.generate(cols, (col) {
                final tx = cx + col - (cols ~/ 2);
                final ty = cy + row - (rows ~/ 2);
                final url =
                    'https://tile.openstreetmap.org/$zoom/$tx/$ty.png';
                return SizedBox(
                  width: tileSize,
                  height: tileSize,
                  child: CachedNetworkImage(
                    imageUrl: url,
                    fit: BoxFit.cover,
                    placeholder: (_, __) =>
                        const ColoredBox(color: Color(0xFFE8E8E8)),
                    errorWidget: (_, __, ___) =>
                        const ColoredBox(color: Color(0xFFE8E8E8)),
                  ),
                );
              }),
            );
          }),
        ),
      ),
    );
  }

  Widget _buildMapsButton() {
    return Material(
      color: AppColors.white,
      elevation: 2,
      shadowColor: const Color(0x40000000),
      borderRadius: BorderRadius.circular(AppRadius.full),
      child: InkWell(
        onTap: _openMapsExternally,
        borderRadius: BorderRadius.circular(AppRadius.full),
        child: Padding(
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.s3,
            vertical: AppSpacing.s2,
          ),
          child: Text(
            mapsButtonLabel,
            style: AppTypography.bodySmEmphasized.copyWith(
              color: AppColors.black,
            ),
          ),
        ),
      ),
    );
  }

  // ──────────────────────────────────────────────────────────────────────────
  // Actions
  // ──────────────────────────────────────────────────────────────────────────

  Future<void> _openMapsExternally() async {
    final primary = externalMapUrl?.trim();
    final embed = normalizeLocalisationEmbedInput(embedUrl);
    final comp = complement.trim();

    Uri? target;
    if (primary != null && primary.isNotEmpty) {
      target = _parseHttpUri(primary);
    }
    if (target == null && embed.isNotEmpty) {
      target = _parseHttpUri(embed);
    }
    if (target == null && comp.isNotEmpty) {
      target = Uri.parse(
        'https://www.google.com/maps/search?q=${Uri.encodeComponent(comp)}',
      );
    }
    if (target == null) return;

    if (await canLaunchUrl(target)) {
      await launchUrl(target, mode: LaunchMode.externalApplication);
    }
  }

  static Uri? _parseHttpUri(String raw) {
    final s = raw.startsWith('http') ? raw : 'https://$raw';
    return Uri.tryParse(s);
  }
}
