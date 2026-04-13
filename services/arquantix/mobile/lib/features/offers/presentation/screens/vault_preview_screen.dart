import 'package:flutter/material.dart';

import '../../../../design_system/design_system.dart';
import '../../../favorites/data/favorites_api.dart';
import '../../data/vault_builder_api.dart';
import '../../../landing_preview/data/landing_page_builder_api.dart';
import '../../../landing_preview/presentation/screens/landing_page_preview_screen.dart';

/// Écran qui charge un vault puis affiche son contenu via [LandingPagePreviewScreen].
class VaultPreviewScreen extends StatefulWidget {
  const VaultPreviewScreen({super.key, required this.slug});

  final String slug;

  /// Ouvre un vault en push (charge puis affiche le contenu).
  static Future<void> open(BuildContext context, String slug) {
    return Navigator.of(context).push<void>(
      MaterialPageRoute<void>(
        builder: (_) => VaultPreviewScreen(slug: slug),
      ),
    );
  }

  @override
  State<VaultPreviewScreen> createState() => _VaultPreviewScreenState();
}

class _VaultPreviewScreenState extends State<VaultPreviewScreen> {
  final VaultBuilderApi _api = VaultBuilderApi();
  final FavoritesApi _favoritesApi = FavoritesApi();
  bool _loading = true;
  String? _error;
  LandingPagePayload? _payload;
  bool _isFavorite = false;
  String? _favoriteId;

  @override
  void initState() {
    super.initState();
    _load();
    _loadFavoriteStatus();
  }

  Future<void> _loadFavoriteStatus() async {
    try {
      final favs = await _favoritesApi.fetchFavorites(entityType: 'exclusive_offer');
      if (!mounted) return;
      final match = favs.where((f) => f.entityId == widget.slug).toList();
      setState(() {
        _isFavorite = match.isNotEmpty;
        _favoriteId = match.isNotEmpty ? match.first.id : null;
      });
    } catch (_) {}
  }

  Future<void> _toggleFavorite() async {
    if (_isFavorite && _favoriteId != null) {
      final ok = await _favoritesApi.removeFavorite(_favoriteId!);
      if (ok && mounted) {
        setState(() {
          _isFavorite = false;
          _favoriteId = null;
        });
      }
    } else {
      final result = await _favoritesApi.addFavorite(
        entityType: 'exclusive_offer',
        entityId: widget.slug,
      );
      if (result.isSuccess && result.favorite != null && mounted) {
        setState(() {
          _isFavorite = true;
          _favoriteId = result.favorite!.id;
        });
      } else if (!result.isSuccess && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(result.messageForUser()),
            duration: const Duration(seconds: 3),
          ),
        );
      }
    }
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final payload = await _api.fetchBySlug(widget.slug, draft: false);
      if (!mounted) return;
      setState(() {
        _payload = payload;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return Scaffold(
        backgroundColor: AppColors.pageBackground,
        body: const Center(child: CircularProgressIndicator()),
      );
    }
    if (_error != null) {
      return Scaffold(
        backgroundColor: AppColors.pageBackground,
        appBar: AppBar(
          title: const Text('Vault'),
          leading: IconButton(
            icon: const Icon(Icons.arrow_back),
            onPressed: () => Navigator.of(context).pop(),
          ),
        ),
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(AppSpacing.xl),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Text(
                  _error!,
                  style: AppTypography.bodyMedium,
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: AppSpacing.lg),
                TextButton.icon(
                  onPressed: _load,
                  icon: const Icon(Icons.refresh, size: 20),
                  label: const Text('Réessayer'),
                ),
              ],
            ),
          ),
        ),
      );
    }
    if (_payload != null) {
      return LandingPagePreviewScreen(
        initialSlug: widget.slug,
        preloadedPayload: _payload,
        controlsEnabled: false,
        onRefresh: _load,
        extraNavBarActions: [
          AppTopNavBarAction(
            icon: _isFavorite ? Icons.star_rounded : Icons.star_outline,
            iconColor: _isFavorite ? const Color(0xFFFFB800) : null,
            onPressed: _toggleFavorite,
          ),
        ],
      );
    }
    return Scaffold(
      backgroundColor: AppColors.pageBackground,
      body: const Center(child: Text('Vault introuvable')),
    );
  }
}
